import re
from llparser import *

# test system
if 1: # just for folding
	USE_RE = True
	# скорее всего использование регулярных выражений будет более эфективным
	# но для отладки функций парсинга мы договариваемся вообще не использовать регулярные выражения
	def re_enable():
		global USE_RE
		USE_RE = True
	def re_disable():
		global USE_RE
		USE_RE = False

	class Err: # short error
		def __init__(self,*args):
			self.x=args
		def __repr__(self):
			return 'Err'+repr(tuple(self.x))

	def ptest(patt,string,stopstr=' '):
		global USE_RE
		tmp = USE_RE
		try:
			USE_RE = True
			reset_errors_warnings()
			rt= read_sequence(string+stopstr,mkpos(0), a=patt,b=stopstr,proc=lambda d : d.a)
			rt, errors_copy, warnings_copy = extract_errors_warnings(rt)

			USE_RE = False
			reset_errors_warnings()
			rf= read_sequence(string+stopstr,mkpos(0), a=patt,b=stopstr,proc=lambda d : d.a)
			rf, ERRORS, WARNINGS = extract_errors_warnings(rf)
			if ERRORS!=errors_copy:
				print('different errors:')
				print('with re:',errors_copy)
				print('without re:',ERRORS)
			else:
				if len(ERRORS):
					print('errors:',ERRORS)
			if WARNINGS!=warnings_copy:
				print('different warnings:')
				print('with re:',warnings_copy)
				print('without re:',WARNINGS)
			else:
				if len(WARNINGS):
					print('warnings:',WARNINGS)
		finally:
			USE_RE = tmp
		if isok(rt) and isok(rf):
			if rt==rf:
				return rt
			else:
				return mkdict(with_re=rt,without_re=rf)
		elif not isok(rt) and not isok(rf):
			if rt.details.short()==rf.details.short():
				return Err(*rt.details.short())
			else:
				return mkdict(with_re=rt,without_re=rf)
		return mkdict(with_re=rt,without_re=rf)

# punctuator, digit, hexadecimal_digit, octal_digit, nondigit
# hexadecimal_prefix, hex_quad, universal_character_name, identifier
if 1: # just for folding

	digit             = char_in_set('0123456789'               ,errproc='digit')
	hexadecimal_digit = char_in_set('0123456789abcdefABCDEF'   ,errproc='hexadecimal digit')
	octal_digit       = char_in_set('01234567'                 ,errproc='octal digit')
	nondigit          = char_in_set('_'+''.join(chr(i) for i in range(ord('a'),ord('z')+1))+\
										''.join(chr(i) for i in range(ord('A'),ord('Z')+1)),errproc='nondigit')

	@cacheread
	def hexadecimal_prefix(s,pos):
		'''
		>>> ptest(hexadecimal_prefix,'0x')
		'0x'
		>>> ptest(hexadecimal_prefix,'0000')
		Err(0, 'hexadecimal_prefix')
		'''
		if USE_RE:
			return read(s,pos, regexp(r'0[xX]',errproc='hexadecimal_prefix'))
		else:
			return read_oneof(s,pos,'0x','0X',errproc='hexadecimal_prefix')

	@cacheread
	def hex_quad(s,pos): # without universal character name
		'''
		>>> ptest(hex_quad,'0134')
		308
		>>> ptest(hex_quad,'013')
		Err(0, 'hex_quad')
		'''
		if USE_RE:
			return read(s,pos, regexp(r'[0-9a-zA-Z]{4}',errproc='hex_quad',proc = lambda x : int(x[0],16)))
		else:
			return read_sequential(s,pos,a=hexadecimal_digit,b=hexadecimal_digit,c=hexadecimal_digit,d=hexadecimal_digit,
							 proc = dcatf(inthex), errproc = 'hex_quad' ) # almost dcat
								  # lambda d: int(d.a+d.b+d.c+d.d,16)

	@cacheread
	def universal_character_name(s,pos): ## todo изменить возвращаемый тип на int
		r'''
		>>> ptest(universal_character_name,r"\u0130")
		'İ'
		>>> ptest(universal_character_name,r"\U000103a6")
		'𐎦'
		>>> ptest(universal_character_name,r"\U11112222")
		errors: {(0, 10): ProcError('chr() arg not in range(0x110000)')}
		ProcError('chr() arg not in range(0x110000)')
		>>> ptest(universal_character_name,'0134')
		Err(0, 'universal_character_name')
		'''
		def chr_force(i):
			try:
				return chr(i)
			except ValueError as e:
				return ProcError(e.args[0])
		if USE_RE:
			return read(s,pos, regexp(r'\\u[0-9a-zA-Z]{4}|\\U[0-9a-zA-Z]{8}',errproc='universal_character_name',
									  proc=lambda x : chr_force(int(x[0][2:],16))))
		else:
			return read_oneof(s,pos,sequential(a='\\u',b=hex_quad, proc= lambda d: chr(d.b) , errproc= '\\uhhhh' ),
					sequential(a='\\U',b=hex_quad,c=hex_quad, proc= lambda d: chr_force(d.b*65536+d.c) , errproc= '\\Uhhhhhhhh' ),
							 errproc='universal_character_name')

	@cacheread
	def identifier(s,pos):
		'''
		>>> ptest(identifier,'as0df')
		'as0df'
		>>> ptest(identifier,'0as0df')
		Err(0, 'identifier')
		'''
		if USE_RE:
			return read(s,pos, regexp(r'[a-zA-Z_][a-zA_Z0-9_]*',errproc='identifier')) # without universal character name ##todo
		else:
			return read_sequential(s,pos, f=oneof(nondigit,universal_character_name),
										  s=rep_star(oneof(nondigit,universal_character_name,digit), proc=lcat ),
								  proc=dcat, errproc= 'identifier'
								  )


# nonzero_digit, decimal_constant, octal_constant, hexadecimal_digit_sequence, hexadecimal_constant,
# unsigned_suffix, long_suffix, long_long_suffix, integer_suffix, integer_constant
if 1: # just for folding
	nonzero_digit = char_in_set('123456789',errproc='nonzero_digit')

	@cacheread
	def decimal_constant(s,pos):
		'''
		>>> ptest(decimal_constant,'123')
		123
		>>> ptest(decimal_constant,'0123')
		Err(0, 'decimal_constant')
		'''
		if USE_RE:
			return read(s,pos, regexp(r'[1-9][0-9]*',proc = lambda x : int(x[0]), errproc='decimal_constant'))
		else:
			return read_sequential(s,pos, f=nonzero_digit, s=rep_star(digit, proc=lcat) ,
								  proc=dcatf(int), errproc= 'decimal_constant'
								  )

	@cacheread
	def octal_constant(s,pos):
		'''
		>>> ptest(octal_constant,'0123')
		83
		>>> ptest(octal_constant,'0')
		0
		>>> ptest(octal_constant,'123')
		Err(0, 'octal_constant')
		'''
		if USE_RE:
			return read(s,pos, regexp(r'0[0-7]*',proc = lambda x : int(x[0],8), errproc='octal_constant'))
		else:
			return read_sequential(s,pos, f='0', s=rep_cat(0,infinity,octal_digit) ,
								  proc=lambda d: int(d.s,8) if len(d.s) else 0, errproc= 'octal_constant' #
								  )

	@cacheread
	def hexadecimal_digit_sequence(s,pos):
		'''
		>>> ptest(hexadecimal_digit_sequence,'123')
		mkfdict(v=291, l=3)
		>>> ptest(hexadecimal_digit_sequence,'00123')
		mkfdict(v=291, l=5)
		>>> ptest(hexadecimal_digit_sequence,'-123')
		Err(0, 'hexadecimal_digit_sequence')
		'''
		def foo(l):
			s = ''.join(l)
			return mkfdict(v=inthex(s),l=len(s))
		if USE_RE:
			return read(s,pos, regexp(r'[0-9a-fA-F]+',proc = lambda x : mkfdict(v=int(x[0],16),l=len(x[0])), errproc='hexadecimal_digit_sequence'))
		else:
			return read_repeatedly(s,pos, 1,infinity,hexadecimal_digit, proc=foo, errproc= 'hexadecimal_digit_sequence')

	@cacheread
	def hexadecimal_constant(s,pos):
		'''
		>>> ptest(hexadecimal_constant,'0x123')
		291
		>>> ptest(hexadecimal_constant,'0x-123')
		Err(0, 'hexadecimal_constant')
		>>> ptest(hexadecimal_constant,'123')
		Err(0, 'hexadecimal_constant')
		'''
		if USE_RE:
			return read(s,pos, regexp(r'0[xX][0-9a-fA-F]+',proc = lambda x : int(x[0],16), errproc='hexadecimal_constant'))
		else:
			return read_sequential(s,pos, f=oneof('0x','0X'), s=hexadecimal_digit_sequence ,
								  proc=lambda d: d.s.v, errproc= 'hexadecimal_constant'
								  )

	unsigned_suffix = char_in_set('uU',errproc='unsigned_suffix')
	long_suffix     = char_in_set('lL',errproc='long_suffix')

	@cacheread
	def long_long_suffix(s,p):
		if USE_RE:
			return read(s,p, regexp(r'll|LL', errproc='long_long_suffix'))
		else:
			return read_oneof(s,p, 'll', 'LL', errproc='long_long_suffix')

	@cacheread
	def integer_suffix(s,p):
		'''
		>>> ptest(integer_suffix,'u')
		mkfdict(unsigned=True, long=0)
		>>> ptest(integer_suffix,'uLL')
		mkfdict(unsigned=True, long=2)
		'''
		def final_proc(s):
			d = AttrDict()
			d.unsigned =  'u' in s or 'U' in s
			d.long = 2 if 'll' in s or 'LL' in s else \
					1 if 'l' in s or 'L' in s else \
					0
			return FrozenAttrDict(d)
		def proc_first(proc):
			def f(p):
				a,b = p
				a = proc(a)
				return (a,b)
			return f

		if USE_RE:
			return read(s,p, regexp(r'[uU](ll|LL|[lL])?|[lL][uU]?|(ll|LL)[uU]?', errproc='integer_suffix',
								   proc=lambda x : final_proc(x[0])))
		else:
			lL = char_in_set('lL')
			uU = char_in_set('uU')
			return read_atleast_oneof(s,p, a=seq_cat(a=uU,b=opt_des(atleast_oneof(a='ll',b='LL',c=lL,proc=select_longest))),
									b=seq_cat(a=lL,b=opt_des(uU)),
									c=seq_cat(a=oneof('ll','LL'),b=opt_des(uU)),
							  proc=compose(proc_first(final_proc),select_longest),errproc='integer_suffix')
	@cacheread
	def integer_constant(s,p):
		'''
		>>> ptest(integer_constant,'5')
		mkfdict(unsigned=False, long=0, value=5)
		>>> ptest(integer_constant,'0x5u')
		mkfdict(unsigned=True, long=0, value=5)
		>>> ptest(integer_constant,'0')
		mkfdict(unsigned=False, long=0, value=0)
		'''
		return read_sequential(s,p, i=atleast_oneof(a=decimal_constant,b=octal_constant,c=hexadecimal_constant,proc=select_longest),
									s=optional(integer_suffix,proc=dflt(mkfdict(unsigned=False,long=0))),
							 proc=lambda d: dict_append(d.s,value=d.i),errproc='integer_constant')

# floating_suffix, sign, fractional_constant, exponent_part, decimal_floating_constant, my_hexadecimal_fractional_constant
# binary_exponent_part, hexadecimal_floating_constant, floating_constant
if 1: # just for folding
	floating_suffix = char_in_set('fFlL',proc=lambda c : 'float' if c in 'fF' else 'long_double',errproc='char_in_set')
	sign = char_in_set('+-',errproc='sign')
	@cacheread
	def fractional_constant(s,p):
		'''
		>>> ptest(fractional_constant,'2.')
		'2.'
		>>> ptest(fractional_constant,'.')
		Err(0, 'fractional_constant')
		'''
		if USE_RE:
			return read(s,p,regexp(r'[0-9]*\.[0-9]+|[0-9]+\.',errproc='fractional_constant'))
		else:
			return read_oneof(s,p, seq_cat(a=rep_cat(1,infinity,digit),b='.',c=rep_cat(0,infinity,digit)),
								 seq_cat(b='.',c=rep_cat(1,infinity,digit)), errproc='fractional_constant')
	@cacheread
	def exponent_part(s,p):
		'''
		>>> ptest(exponent_part,'e76')
		'e76'
		>>> ptest(exponent_part,'E-0')
		'E-0'
		>>> ptest(exponent_part,'.')
		Err(0, 'exponent_part')
		'''
		if USE_RE:
			return read(s,p,regexp(r'[eE][+-]?[0-9]+',errproc='exponent_part'))
		else:
			return read(s,p, seq_cat(a=char_in_set('eE'),b=opt_des(char_in_set('+-')),c=rep_cat(1,infinity,digit), errproc='exponent_part'))
	@cacheread
	def decimal_floating_constant(s,p): # ignore long double ##todo
		'''
		>>> ptest(decimal_floating_constant,'5e2')
		mk_fo_dict(value=500.0, type='double')
		>>> ptest(decimal_floating_constant,'0.f')
		mk_fo_dict(value=0.0, type='float')
		>>> ptest(decimal_floating_constant,'0.e')
		Err(2, ' ')
		>>> ptest(decimal_floating_constant,'1e-5L')
		mk_fo_dict(value=1e-05, type='long_double')
		>>> ptest(decimal_floating_constant,'1')
		Err(0, 'decimal_floating_constant')
		'''
		if USE_RE:
			return read_sequence(s,p,value=regexp(r'[0-9]*\.[0-9]+|[0-9]+\.([eE][+-]?[0-9]+)?|[0-9]+[eE][+-]?[0-9]+',proc= lambda x: float(x[0])),
								 type=optional(floating_suffix,proc=dflt('double')), errproc='decimal_floating_constant')
		else:
			return read_sequence(s,p,value=oneof(seq_cat(a=fractional_constant,b=opt_des(exponent_part)),
												 seq_cat(a=rep_cat(1,infinity,digit),b=exponent_part),
												 proc= lambda x: float(x)),
								 type=optional(floating_suffix,proc=dflt('double')), errproc='decimal_floating_constant')
	@cacheread
	def my_hexadecimal_fractional_constant(s,p):
		r'''
		hs(\.hs?)?|\.hs
		>>> ptest(my_hexadecimal_fractional_constant,'2')
		2.0
		>>> ptest(my_hexadecimal_fractional_constant,'2.')
		2.0
		>>> ptest(my_hexadecimal_fractional_constant,'.2')
		0.125
		>>> ptest(my_hexadecimal_fractional_constant,'.')
		Err(0, 'my_hexadecimal_fractional_constant')
		'''
		hs = hexadecimal_digit_sequence
		return read_oneof(s,p, sequential(a=hs,
										  b=optional(sequential(a='.',b=optional(hs,proc=dflt(mkfdict(v=0,l=0))),proc=lambda d: d.b.v/16**d.b.l),proc=dflt(0.)),
										  proc= lambda d:d.a.v+d.b),
						 sequential(a='.',b=hs,proc=lambda d: d.b.v/16**d.b.l),errproc='my_hexadecimal_fractional_constant')
	@cacheread
	def binary_exponent_part(s,p):
		'''
		>>> ptest(binary_exponent_part,'p76')
		76
		>>> ptest(binary_exponent_part,'P-0')
		0
		>>> ptest(binary_exponent_part,'.')
		Err(0, 'binary_exponent_part')
		'''
		if USE_RE:
			return read(s,p,regexp(r'[pP][+-]?[0-9]+',proc= lambda x  : int(x[0][1:]),errproc='binary_exponent_part'))
		else:
			return read_sequential(s,p, a=char_in_set('pP'),b=optional(char_in_set('+-'),proc=dflt('+')),c=rep_cat(1,infinity,digit),
							  proc=lambda d : int(d.c) if d.b=='+' else -int(d.c),
							  errproc='binary_exponent_part')
	@cacheread
	def hexadecimal_floating_constant(s,p): # ignore long double ##todo
		'''
		>>> ptest(hexadecimal_floating_constant,'0x5p2')
		mkfdict(value=20.0, type='double')
		>>> ptest(hexadecimal_floating_constant,'0x0.p0f')
		mkfdict(value=0.0, type='float')
		>>> ptest(hexadecimal_floating_constant,'0x0.p')
		Err(0, 'hexadecimal_floating_constant')
		>>> ptest(hexadecimal_floating_constant,'0x1p-5L')
		mkfdict(value=0.03125, type='long_double')
		>>> ptest(hexadecimal_floating_constant,'0x1')
		Err(0, 'hexadecimal_floating_constant')
		'''
		if USE_RE:
			prefix=regexp('0x|0X')
		else:
			prefix=oneof('0x','0X')
		return read_sequence(s,p,pref=prefix,value=my_hexadecimal_fractional_constant,exp=binary_exponent_part,
							 type=optional(floating_suffix,proc=dflt('double')),
							 proc=lambda d : mkfdict(value=d.value*2**d.exp,type=d.type),
							 errproc='hexadecimal_floating_constant')
	def floating_constant(s,p):
		return read_oneof(s,p,hexadecimal_floating_constant,decimal_floating_constant)

# simple_escape_sequence, octal_escape_sequence, hexadecimal_escape_sequence, escape_sequence
# character_constant, string_literal
if 1: # just for folding
	@cacheread
	def simple_escape_sequence(s,p):
		r'''
		>>> ptest(simple_escape_sequence,r'\n')
		'\n'
		>>> ptest(simple_escape_sequence,r'\a')
		'\x07'
		>>> ptest(simple_escape_sequence,r'\c')
		Err(0, 'simple_escape_sequence')
		'''
		def rise_func():
			raise ValueError()
		def proc(x):
			return  "'" if x=="'" else\
					'"' if x=='"' else\
					'?' if x=='?' else\
					'\\' if x=='\\' else\
					'\a' if x=='a' else\
					'\b' if x=='b' else\
					'\f' if x=='f' else\
					'\n' if x=='n' else\
					'\r' if x=='r' else\
					'\t' if x=='t' else\
					'\v' if x=='v' else rise_func()
		if USE_RE:
			return read(s,p, regexp(r'\\([\'"?\\abfnrtv])',proc=lambda x: proc(x[1]),errproc='simple_escape_sequence'))
		else:
			return read_sequence(s,p, a='\\',b=char_in_set('\'"?\\abfnrtv'),proc=lambda d: proc(d.b),errproc='simple_escape_sequence')

	@cacheread
	def octal_escape_sequence(s,p):
		r'''
		>>> ptest(octal_escape_sequence,r'\1')
		'\x01'
		>>> ptest(octal_escape_sequence,r'\12')
		'\n'
		>>> ptest(octal_escape_sequence,r'\123')
		'S'
		>>> ptest(octal_escape_sequence,r'\1234')
		Err(4, ' ')
		'''
		if USE_RE:
			return read(s,p, regexp(r'\\([0-7]([0-7][0-7]?)?)',proc=lambda x: chr(intoct(x[1])),errproc='octal_escape_sequence'))
		else:
			return read_sequence(s,p, a='\\',b=seq_cat(a=octal_digit,b=opt_des(seq_cat(a=octal_digit,b=opt_des(octal_digit))))
								 ,proc=lambda x:chr(intoct(x.b)) ,errproc='octal_escape_sequence')

	@cacheread
	def hexadecimal_escape_sequence(s,p):
		r'''
		>>> ptest(hexadecimal_escape_sequence,r'\x1')
		warnings: {(0, 3): ProcWarning('\x01', 'too short hexadecimal escape sequence')}
		'\x01'
		>>> ptest(hexadecimal_escape_sequence,r'\x12')
		'\x12'
		>>> ptest(hexadecimal_escape_sequence,r'\x123')
		errors: {(0, 5): ProcError('Long hexadecimal escape sequence not supported. Use universal character name.')}
		ProcError('Long hexadecimal escape sequence not supported. Use universal character name.')
		'''
		def proc(s):
			if len(s)>2:
				return ProcError('Long hexadecimal escape sequence not supported. Use universal character name.')
			elif len(s)==1:
				return ProcWarning(chr(inthex(s)),'too short hexadecimal escape sequence')
			return chr(inthex(s))
		if USE_RE:
			return read(s,p, regexp(r'\\x([0-9a-fA-F]+)',proc=lambda x: proc(x[1]),errproc='hexadecimal_escape_sequence'))
		else:
			return read_sequence(s,p, a='\\x',b=rep_cat(1,infinity,hexadecimal_digit)
								 ,proc=lambda x:proc(x.b) ,errproc='hexadecimal_escape_sequence')

	@cacheread
	def escape_sequence(s,p):
		r'''
		>>> ptest(escape_sequence,r'\u0130')
		'İ'
		>>> ptest(escape_sequence,'')
		Err(0, 'escape_sequence')
		'''
		return read_oneof(s,p,simple_escape_sequence, octal_escape_sequence, hexadecimal_escape_sequence, universal_character_name,errproc='escape_sequence')

	@cacheread
	def character_constant(s,p):
		r"""
		>>> ptest(character_constant,"'x'")
		mkfdict(type='char', value='x')
		>>> ptest(character_constant,r"U'\n'")
		mkfdict(type='char32_t', value='\n')
		>>> ptest(character_constant,"'xy'")
		Err(0, 'character_constant')
		>>> ptest(character_constant,"''")
		Err(0, 'character_constant')
		"""
		if USE_RE:
			char = regexp(r'[^\'\\\n]')
		else:
			char = char_not_in_set('\'\\\n')
		return read_sequence(s,p, type=optional(char_in_set('LuU',proc=lambda x:'wchar_t' if x=='L' else 'char16_t' if x=='u' else 'char32_t'),dflt('char')),
							open="'", value=oneof(char,escape_sequence),close="'",proc=lambda d: dict_delete(d,open=0,close=0),
							errproc='character_constant')

	@cacheread
	def string_literal(s,p):
		r"""
		>>> ptest(string_literal,'"x"')
		mkfdict(type='char', value=b'x')
		>>> ptest(string_literal,r'U"\n"')
		mkfdict(type='char32_t', value=b'\n\x00\x00\x00')
		>>> ptest(string_literal,'"xy"')
		mkfdict(type='char', value=b'xy')
		>>> ptest(string_literal,'""')
		mkfdict(type='char', value=b'')

		>>> ptest(string_literal,r'"\x20"')
		mkfdict(type='char', value=b' ')
		>>> ptest(string_literal,r'"\x99"')
		mkfdict(type='char', value=b'\x99')
		>>> ptest(string_literal,r'"\u0100"')
		warnings: {(0, 8): ProcWarning(mkfdict(type='char', value=b'?'), 'at position 0 ordinal not in range(256)')}
		mkfdict(type='char', value=b'?')

		>>> ptest(string_literal,r'u8"\x20"')
		mkfdict(type='char', value=b' ')
		>>> ptest(string_literal,r'u8"\x99"')
		mkfdict(type='char', value=b'\xc2\x99')
		>>> ptest(string_literal,r'u8"\u0100"')
		mkfdict(type='char', value=b'\xc4\x80')
		>>> ptest(string_literal,r'u8"\ud801"')
		warnings: {(0, 10): ProcWarning(mkfdict(type='char', value=b'\xed\xa0\x81'), 'at position 0 surrogates not allowed')}
		mkfdict(type='char', value=b'\xed\xa0\x81')

		>>> ptest(string_literal,r'u"\x20"')
		mkfdict(type='char16_t', value=b' \x00')
		>>> ptest(string_literal,r'u"\x99"')
		mkfdict(type='char16_t', value=b'\x99\x00')
		>>> ptest(string_literal,r'u"\u0100"')
		mkfdict(type='char16_t', value=b'\x00\x01')
		>>> ptest(string_literal,r'u"\ud801"')
		warnings: {(0, 9): ProcWarning(mkfdict(type='char16_t', value=b'\x01\xd8'), 'at position 0 surrogates not allowed')}
		mkfdict(type='char16_t', value=b'\x01\xd8')
		>>> ptest(string_literal,r'u"\U00012282"')
		mkfdict(type='char16_t', value=b'\x08\xd8\x82\xde')
		>>> ptest(string_literal,r'u"\U00112222"') ## todo ProcWarning
		errors: {(2, 12): ProcError('chr() arg not in range(0x110000)')}
		ProcError('chr() arg not in range(0x110000)')
		"""
		def proc_fun(d):
			value = d.value
			typ = d.type
			if d.type=='wchar_t' or d.type=='char32_t':
				try:
					value = d.value.encode(encoding='utf_32_le')
				except UnicodeEncodeError as e:
					value = d.value.encode(encoding='utf_32_le',errors='surrogatepass')
					return ProcWarning(FrozenAttrDict(type=typ,value=value),f'at position {e.start} {e.reason}')
			elif d.type=='char16_t':
				try:
					value = d.value.encode(encoding='utf_16_le')
				except UnicodeEncodeError as e:
					value = d.value.encode(encoding='utf_16_le',errors='surrogatepass')
					return ProcWarning(FrozenAttrDict(type=typ,value=value),f'at position {e.start} {e.reason}')
			elif d.type=='char8_t':
				typ = 'char'
				try:
					value = d.value.encode(encoding='utf_8')
				except UnicodeEncodeError as e:
					value = d.value.encode(encoding='utf_8',errors='surrogatepass')
					return ProcWarning(FrozenAttrDict(type=typ,value=value),f'at position {e.start} {e.reason}')
			elif d.type=='char':
				try:
					value = d.value.encode(encoding='latin1')
				except UnicodeEncodeError as e:
					value = d.value.encode(encoding='latin1',errors='replace')
					return ProcWarning(FrozenAttrDict(type=typ,value=value),f'at position {e.start} {e.reason}')
			else: assert False
			return FrozenAttrDict(type=typ,value=value)
		if USE_RE:
			char = regexp(r'[^\"\\\n]')
		else:
			char = char_not_in_set("\"\\\n")
		return read_sequence(s,p, type=optional(proc(atleast_oneof(a='L',b='u',c='U',d='u8',proc=select_longest),
									lambda x:'wchar_t' if x=='L' else 'char16_t' if x=='u' else 'char32_t' if x=='U' else 'char8_t'),dflt('char')),
							open='"', value=rep_cat(0,infinity,oneof(regexp(r'[^\"\\\n]'),escape_sequence)),close='"',
							proc=lambda d: proc_fun(dict_delete(d,open=0,close=0)),
							errproc='string_literal')

	## todo как отдельная экпериментальная ветка (посмотреть на производительность):
	#       чтобы обработчики могли ощаться через глобальный словарь ENVIRONMENT
	#       в каждой возможной точке возврата это словарь надо копировать, и при возврате восстанавливать
	#       !!! этот словарь хранить в переменной pos

if 1:
	@cacheread
	def spc(s,p):
		'''
		>>> ptest(spc,' ')
		' '
		>>> ptest(spc,'.')
		Err(0, 'spc')
		'''
		return read(s,p,char_in_set(' \t\r\n\v',errproc='spc'))
	@cacheread
	def spcs(s,p):
		r'''
		>>> ptest(spcs,' ',stopstr='-')
		' '
		>>> ptest(spcs,' \n ',stopstr='-')
		' \n '
		>>> ptest(spcs,'',stopstr='-')
		''
		>>> ptest(spcs,'.')
		Err(0, ' ')
		'''
		if USE_RE:
			return read(s,p,regexp(r'[ \t\r\n\v]*'))
		else:
			return read_repeatedly(s,p,0,infinity,spc,proc=lcat,errproc='spcs')
	end_of_line = oneof('\n','\r\n','\r',end_of_stream)
	start_oneline_comment = fix_str('//')
	start_multiline_comment = fix_str('/*')
	def rest_oneline_comment(s,p):
		r'''
		>>> ptest(rest_oneline_comment,'',stopstr='')
		''
		>>> ptest(rest_oneline_comment,'qwerk',stopstr='')
		'qwerk'
		>>> ptest(rest_oneline_comment,'qwerk\n')
		'qwerk'
		'''
		if USE_RE:
			return read(s,p,regexp(r'([^\n]*)(\n)?', lambda x: x[1], errproc='rest_oneline_comment'))
		else:
			return read_repeatedly_until(s,p,char_not_in_set('\n'),end_of_line, proc = lambda l : lcat(l[:-1]), errproc ='rest_oneline_comment')
	def rest_multiline_comment(s,p):
		r'''
		>>> ptest(rest_multiline_comment,'',stopstr='')
		mkfdict(text='', finalized=False)
		>>> ptest(rest_multiline_comment,'qwer',stopstr='')
		mkfdict(text='qwer', finalized=False)
		>>> ptest(rest_multiline_comment,'qwer\n')
		mkfdict(text='qwer', finalized=False)
		>>> ptest(rest_multiline_comment,'qwer*/')
		mkfdict(text='qwer', finalized=True)
		>>> ptest(rest_multiline_comment,'qwer**/')
		mkfdict(text='qwer*', finalized=True)
		>>> ptest(rest_multiline_comment,'qwer* /',stopstr='')
		mkfdict(text='qwer* /', finalized=False)
		'''
		if USE_RE:
			return read(s,p,regexp(r'(((?!\*\/)[^\n])*)(\*\/|\n|$)',lambda x: mkfdict(text=x[1],finalized=x[3]=='*/'), 
				errproc ='rest_multiline_comment'))
		else:
			return read_repeatedly_until(s,p,char_not_in_set('\r\n'),oneof('*/',end_of_line,proc=lambda x:x=='*/'),
				proc=lambda l : mkfdict(text=lcat(l[:-1]),finalized=l[-1]), errproc ='rest_multiline_comment'
			)
	def punctuator(s,p):
		'''
		>>> ptest(punctuator,'+')
		'+'
		>>> ptest(rep_cat(0,infinity,punctuator),'+++')
		'+++'
		>>> ptest(rep_cat(0,infinity,punctuator),'/*+')
		Err(0, ' ')
		'''
		return read_atleast_oneof(s,p, a=char_in_set('[](){}<>.,+-&*/~!%=^|?:;#'), notol=start_oneline_comment, notml=start_multiline_comment,
			proc=compose(select_longest,filter_not),errproc='punctuator')

if __name__ == "__main__":
	read('/** @file form3.h',mkpos(0),sequence(a=spcs, b=rep_star(token_s)))
	import doctest
	caching_set(False)
	print('caching disabled:',doctest.testmod())
	caching_set(True)
	print('caching  enabled:',doctest.testmod())
