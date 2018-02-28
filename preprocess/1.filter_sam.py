import re, sys
from string import maketrans

# Filter SAM file by percent identity and length
# usage: perl 1.filter_sam.pl [sam_file] [percent_id] [min_length]

def decode_cigar(cigar):
    res = []
    hbeg = 0
    alnlen = 0
    hend = 0
    tlen = 0
    tabs = re.split('([a-zA-Z])', cigar)[:-1]
    for i in range(len(tabs)/2):
        ci = int(tabs[i*2])
        li = tabs[i*2 + 1]
        if li == 'H':
            if i == 0:
                hbeg += ci
            else:
                hend += ci
        if li == 'M':
            alnlen += ci
        if li != 'H' and li != 'D':
            tlen += ci
    return [hbeg, alnlen, hend, tlen]


def reverse_complement(seq):
    return seq.translate(maketrans('ACGTacgtNn', 'TGCAtgcaNn'))[::-1]


# read command line arguments
fn = sys.argv[1]
pctid = float(sys.argv[2])
minlen = int(sys.argv[3])


# initialize variables
cquery = ''
cseq = ''
cqual = ''
cflag = 1
cstrand = ''


# parse file
for line in open(fn):

    # print header
    if line.startswith('@'):
        print line.rstrip()
        continue

    # get fields
    sline = line.rstrip().split('\t')
    query = sline[0]
    code = bin(int(sline[1]))[2:].zfill(12)
    strand = int(code[-5])
    ref = sline[2]
    cigar = sline[5]
    cigar = re.sub('H','S',cigar)
    sline[5] = cigar
    seq = sline[9]
    qual = sline[10]

    # skip empty hits
    if ref == '*' or cigar == '*':
        continue

    # make sure read is mapped
    if int(code[-3]) == 1:
        print 'ERROR 0'
        quit()

    # calculate edit distance, total length
    [hbeg, alen, hend, tlen] = decode_cigar(cigar)
    mismatch = int(re.search('[NX]M:i:(\d+)', line).group(1))
    match = alen - mismatch

    # handle empty seq, qual fields
    if (seq == '*' or qual == '*') and (cquery != query):
        print 'ERROR 1'
        quit()

    # update current seq, qual
    if cquery != query:
        if seq == '*' or qual == '*':
            print 'ERROR 2'
            quit()
        cquery = query
        cseq = seq
        cqual = qual
        cstrand = strand
        cflag = 1
    
    # filter by percent identity
    if 1.*match/tlen < 1.*pctid/100.:
        continue
    
    # always set the seq/qual columns
    if strand == cstrand:
        sline[9] = cseq
        sline[10] = cqual
    else:
        sline[9] = reverse_complement(cseq)
        sline[10] = reverse_complement(cseq)
    
    # ensure that the cigar matches the sequence
    if tlen != (len(cseq) - hbeg - hend):
        print 'error: length mismatch'
        print '\n\n%s\n\n%s\n%d %d %d\n%s\n' %(cigar, line.rstrip(), hbeg, hend, len(cseq), cseq)
        quit()
    
    # finally, print quality filtered line
    print '\t'.join(sline)