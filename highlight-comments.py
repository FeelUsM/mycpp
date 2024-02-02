import os
import doctest
from collections import OrderedDict
from llparser import *
from tokens import *
from datetime import datetime

def strip_baks_comment(lines):
	r'''
	>>> [x for x in strip_baks_comment([(1,'aaa /*$bbbb$*/cccc'), (2,'aaa //$bbb\\'), (3,'aaa /*$bbbb$*/cccc /*$zzz$*/aaa //$bbb'), (4,'abc')])]
	[(1, 'aaacccc'), (2, 'aaa\\'), (3, 'aaaccccaaa'), (4, 'abc')]
	'''
	for ln,l in lines:
		#print()
		#print(l+'|')
		r = ''
		p=0
		while (q:=l[p:].find(' /*$')) !=-1:
			q+=p
			r+=l[p:q]
			p = l[q+3:].index('$*/')+3+q+3
			#printpos(q,p)
		if (q:= l[p:].find(' //$')) != -1:
			q+=p
			r+=l[p:q]
			if l[-1]=='\\':
				r+='\\'
			#printpos(q)
		else:
			r+=l[p:]
		yield (ln,r)

def end_merge(lines):
	q=r'''
	>>> [x for x in end_merge([777,'asd'])]
	[(777, 'asd', [])]
	'''
	r=''
	sep_positions = []
	for ln,l in lines:
		if not l.endswith('\\'):
			yield (ln,r+l,sep_positions)
			r=''
			sep_positions=[]
		else:
			r+=l.removesuffix('\\')
			sep_positions.append(sep_positions[-1]+len(l)-1 if len(sep_positions) else len(l)-1)
	if len(sep_positions):
		raise ValueError('aaa')

@cacheread
def token_s(s,p):
	return read_atleast_oneof(s,p,
		id=sequence(a=identifier        ,b=spcs),
		p=sequence(a=punctuator        ,b=spcs),
		int=sequence(a=integer_constant  ,b=spcs),
		fl=sequence(a=floating_constant ,b=spcs),
		ch=sequence(a=character_constant,b=spcs),
		str=sequence(a=string_literal    ,b=spcs),
		proc=select_longest,
		errproc='token_s'
	)

def highlight_comments(lines):
	r'''
	/*x
	x //$ comment
	x //$ comment\
	x*/
	
	//x\
	x /*$ comment $*/\
	x /*$ comment $*/
	'''
	def read_rest_multiline(has_first):
		nonlocal prev_fined
		# clozure : s, pos, sp, ol_insertions
		start = pos.x
		zzz = read(s,pos,rest_multiline_comment)
		assert isok(zzz)
		if not zzz.finalized: # ... \n
			for x in sp:
				if x>=pos.x:
					if has_first:
						ol_insertions.append(x)
					else:
						has_first = True
			if has_first:
				ol_insertions.append(len(s))
			prev_fined = False
		else:
			end = pos.x #  ... */
			for x in sp:
				if x>=start and x<end:
					if has_first:
						ol_insertions.append(x)
					else:
						has_first = True
			prev_fined = True

	ml_insertions = []
	ol_insertions = []
	prev_fined = True # finalized

	for ln,s,sp in lines:
		pos = mkpos(0)
		if not prev_fined: # ... \n or ... */
			read_rest_multiline(True)
		if prev_fined:
			last = pos.x-1
			while pos.x!=len(s):
				if pos.x==last:
					print(len(s),pos.x,repr(s))
					raise Exception()
				else:
					last = pos.x
				try:
					read(s,pos,sequence(a=spcs, b=rep_star(token_s)))
				except BaseException as e:
					print(ln,repr(s))
					raise e
				comm = read(s,pos,start_oneline_comment)
				if isok(comm): # // .... \n
					has_first = False
					for x in sp:
						if x>=pos.x:
							if has_first:
								ml_insertions.append(x)
							else:
								has_first = True
					if has_first:
						ml_insertions.append(len(s))
					read(s,pos,rest_oneline_comment)
				comm = read(s,pos,start_multiline_comment)
				if isok(comm):
					read_rest_multiline(False) # /* ... \n or /* ... */
		assert pos.x==len(s)
		if len(ml_insertions) and len(ol_insertions):
			assert ol_insertions[-1]< ml_insertions[0]

		newsp = []
		news = ''
		pos = 0
		cum_mov = 0
		while len(ml_insertions) or len(ol_insertions) or len(sp):
			if len(ol_insertions) and (len(sp)==0 or ol_insertions[0]<=sp[0]):
				news+= s[pos:ol_insertions[0]]
				pos = ol_insertions[0]
				OLC = ' //$ comment'
				news+= OLC
				cum_mov +=len(OLC)
				del ol_insertions[0]
			if len(ol_insertions)==0 and len(ml_insertions) and (len(sp)==0 or ml_insertions[0]<=sp[0]):
				news+= s[pos:ml_insertions[0]]
				pos = ml_insertions[0]
				MLC = ' //$ comment'
				news+= MLC
				cum_mov +=len(MLC)
				del ml_insertions[0]
			if len(sp) and (len(ml_insertions)==0 or sp[0]<ml_insertions[0]) and (len(ol_insertions)==0 or sp[0]<ol_insertions[0]):
				news+= s[pos:sp[0]]
				pos = sp[0]
				newsp.append(sp[0]+cum_mov)
				del sp[0]
		news+= s[pos:]

		yield (ln,news,newsp)

	if not prev_fined:
		print('error in source: multiline comment not finalized')

def line_split(ln,s,sp):
	cum_mov=0
	news = ''
	pos=0
	while len(sp):
		news+= s[pos:sp[0]]
		pos = sp[0]
		NL = '\\\n'
		news+= NL
		cum_mov +=len(NL)
		del sp[0]
	news+= s[pos:]
	return news

def file_hl_comments(name):
	with open(name, 'r') as file1:
		Lines = [x for x in enumerate(file1.read().split(sep='\n'),1)]
	with open(name, 'w') as file1:
		file1.write('\n'.join(line_split(ln,s,sp) for ln,s,sp in highlight_comments(end_merge(strip_baks_comment(Lines)))))
def file_unhl_comments(name):
	with open(name, 'r') as file1:
		Lines = [x for x in enumerate(file1.read().split(sep='\n'),1)]
	with open(name, 'w') as file1:
		file1.write('\n'.join(line_split(ln,s,sp) for ln,s,sp in (end_merge(strip_baks_comment(Lines)))))

if __name__ == "__main__":
	caching_set(False)
	os.chdir('../form/sources')
	print('total',len([ x for x in os.listdir() if not x.endswith('.h')]))
	for i,x in enumerate(os.listdir()):
		if i>10:
			break
		if x.endswith('.h') or x.endswith('.c') or x.endswith('.cc'):
			print(i,x,datetime.now().strftime("%H:%M:%S"))
			file_hl_comments(x)
			reset_errors_warnings()
