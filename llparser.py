import re
import functools
from collections import OrderedDict
#import copy

# attr ordered dict
if 1: # just for folding
	class AttrDict(dict):
		def __getattr__(self, key):
			if key not in self:
				raise AttributeError(key)
			return self[key]
		def __setattr__(self, key, value):
			self[key] = value
		def __delattr__(self, key):
			del self[key]
		def __repr__(self):
			return 'mkdict('+', '.join(k+'='+repr(v) for k,v in self.items())+')' 
			# если встретиться ключ, который не является строкой, то будет исключение
	def mkdict(**kwargs):
		return AttrDict(kwargs)
	class AttrOrderedDict(OrderedDict):
		def __getattr__(self, key):
			if key not in self:
				raise AttributeError(key)
			return self[key]
		def __setattr__(self, key, value):
			self[key] = value
		def __delattr__(self, key):
			del self[key]
		def __repr__(self):
			return 'mkodict('+', '.join(k+'='+repr(v) for k,v in self.items())+')' 
			# если встретиться ключ, который не является строкой, то будет исключение
	def mkodict(**kwargs):
		return AttrOrderedDict(kwargs)

	class FrozenAttrDict(dict):
		def __getattr__(self, key):
			if key not in self:
				raise AttributeError(key)
			return self[key]
		def _immutable(self, *args, **kws):
			raise TypeError('dict is frozen')
		__setattr__ = _immutable
		__delattr__ = _immutable
		__setitem__ = _immutable
		__delitem__ = _immutable
		pop         = _immutable
		popitem     = _immutable
		clear       = _immutable
		update      = _immutable
		setdefault  = _immutable
		def __repr__(self):
			return 'mkfdict('+', '.join(k+'='+repr(v) for k,v in self.items())+')' 
			# если встретиться ключ, который не является строкой, то будет исключение
	def mkfdict(**kwargs):
		return FrozenAttrDict(kwargs)
	class FrozenAttrOrderedDict(OrderedDict):
		def __init__(self, *args, **kwargs):
			super(FrozenAttrOrderedDict, self).__init__(*args, **kwargs)
			self.__setitem__ = self._immutable
			self.__setattr__ = self._immutable
		def __getattr__(self, key):
			if key not in self:
				raise AttributeError(key)
			return self[key]
		def _immutable(self, *args, **kws):
			raise TypeError('dict is frozen')
		#__setattr__ = _immutable
		__delattr__ = _immutable
		#__setitem__ = _immutable
		__delitem__ = _immutable
		pop         = _immutable
		popitem     = _immutable
		clear       = _immutable
		update      = _immutable
		setdefault  = _immutable
		def __repr__(self):
			return 'mk_fo_dict('+', '.join(k+'='+repr(v) for k,v in self.items())+')'
		# если встретиться ключ, который не является строкой, то будет исключение
	def mk_fo_dict(**kwargs):
		return FrozenAttrOrderedDict(kwargs)
	def mkpos(x):
		return mkdict(x=x)

if 1: # error classes
	class ParseError: # it is not exception
		__slots__ = ['_where','_expected','_details']
		def __init__(self,pos,expected,details=None):
			self._where = pos
			self._expected = expected
			self._details = details
		@property
		def where(self): return self._where
		@where.setter
		def where(self,x):
			assert self._where ==-1
			self._where = x
		@property
		def details(self): return self._details
		@property
		def expected(self): return self._expected
		@expected.setter
		def expected(self,s):  # утвеждается, что сообщения, начинающиеся на @#$ не кэшируются
			tmp = f'{repr(self._expected)}{repr(s)}'
			assert self._expected.startswith('@#$') and not s.startswith('@#$') , tmp
			self._expected = s
		def short(self): return (self._where,self._expected)
		def __repr__(self):
			return f'ParseError({repr(self._where)}, {repr(self._expected)}, {repr(self._details)})'
	def iserr(x):
		return isinstance(x,ParseError) # type(x) is tuple and len(x)>0 and x[0]=='err'
	def isok(x):
		return not iserr(x)
	class ProcWarning:
		'''
		если какой-то обработчик вернул ProcWarning
		этот ProcWarning будет записан в WARNINGS
		после чего из этого ProcWarning будет извлечён результат, который пойдет дальше
		'''
		__slots__ = ['mes','res']
		def __init__(self,res,mes):
			self.res = res
			self.mes = mes
		def __eq__(a,b):
			return (type(a) is type(b)) and (a.mes==b.mes) and (a.res==b.res)
		def __repr__(self):
			return f'ProcWarning({repr(self.res)}, {repr(self.mes)})'
	class ProcError:
		'''
		если какой-то обработчик вернул ProcError, этот ProcError будет распространяться до корня
		парсинг по правилам дальше будет идти как обычно
		но обработчики вызываться не будут
		кроме того этот ProcError будет записан в ERRORS
		'''
		__slots__ = ['mes']
		def __init__(self,mes):
			self.mes = mes
		def __eq__(a,b):
			return (type(a) is type(b)) and (a.mes==b.mes)
		def __repr__(self):
			return f'ProcError({repr(self.mes)})'

if 1: # debug decorator
	DEBUGGING = False
	def debugging_set(x):
		global DEBUGGING
		DEBUGGING = x
	DEBUG_DEPTH = 0
	def debug_start(s,pos,name):
		pref = '\t'*DEBUG_DEPTH
		print(pref,s,'|',sep='')
		print(pref,' '*pos.x,'^-',name,sep='')
	def debug_end(s,start,pos,name,result):
		pref = '\t'*DEBUG_DEPTH
		print(pref,s,'|',sep='')
		if start==pos.x:
			print(pref,' '*start,'V=',repr(result),sep='')
		else:
			print(pref,' '*start,'\\',' '*(pos.x-start-1),'/=',repr(result),sep='')
		return result
	def debug(func,name=None):
		if not DEBUGGING:
			return func
		if name==None:
			name = func.__name__
		@functools.wraps(func)
		def debug_func(s,p):
			global DEBUG_DEPTH
			debug_start(s,p,name)
			DEBUG_DEPTH+=1
			start = p.x
			try:
				r = func(s,p)
			finally:
				DEBUG_DEPTH-=1
			return debug_end(s,start,p,name,r)
		return debug_func

if 1: # cache decorator
	CACHING_ENABLED = True
	def caching_set(x):
		global CACHING_ENABLED
		CACHING_ENABLED = x
	cacheall = lambda func : functools.cache(func) if CACHING_ENABLED else func
	def cacheread(func):
		if not CACHING_ENABLED:
			return debug(func)
		ref_s = ''
		memo = {}
		@functools.wraps(func)
		def wrapper(s,pos):
			nonlocal ref_s, memo
			# reset memo if we start work with new string
			if not (s is ref_s):
				ref_s = s
				memo = {}
			# add the new key to dict if it doesn't exist already
			start = pos.x
			if start not in memo:
				r = func(s,pos)
				stop = pos.x
				# сообщения, начинающиеся с @#$ не должны кэшироваться
				assert not r.expected.startswith('@#$') if isinstance(r,ParseError) else True , 'try to cache unnamed function'+r.expected
				memo[start] = (r,stop) #(copy.deepcopy(r),stop)
			else:
				r,pos.x = memo[start]
			return r
		return debug(wrapper,func.__name__)

if 1: # read proc
	PROC_DEBUG = False
	def proc_debug_set(x):
		global PROC_DEBUG
		PROC_DEBUG = x
	ERRORS = {}
	WARNINGS = {}
	# индексируются парами (начало, конец) разобранного паттерна
	def reset_errors_warnings():
		global ERRORS, WARNINGS
		ERRORS = {}
		WARNINGS = {}
	def extract_errors_warnings(r):
		return (r, ERRORS, WARNINGS)
	def read(s,pos,patt):
		'''
		fun(params)(s,pos) мы заменяем на
		read(s,pos,fun(params))
		'''
		return patt(s,pos)
	def internal_proc(r,start,pos,proc,errproc):
		global ERRORS, WARNINGS
		if isok(r):
			if proc!=None:
				if not isinstance(r,ProcError):
					if PROC_DEBUG:
						print('before: ',r,end='')
					r = proc(r)
					if isinstance(r,ParseError) and r.where==-1:
						r.where = start
					if isinstance(r,ProcError):
						ERRORS[(start,pos.x)] = r
					if isinstance(r,ProcWarning):
						WARNINGS[(start,pos.x)] = r
						r = r.res
					if PROC_DEBUG:
						print(';   after: ',r)
		else:
			if errproc!=None:
				if type(errproc) is str:
					if r.expected==None or r.expected.startswith('@#$'):
						r.expected = errproc
					else:
						r = ParseError(r.where,errproc,r)
				else:
					r= errproc(r)
		assert type(r) is not dict and type(r) is not list and type(r) is not AttrDict and type(r) is not AttrOrderedDict , \
			'result '+repr(type(r))+' '+repr(r)+'should be immutable'
		return r
	def read_proc(s,pos,patt,proc,errproc=None):
		start = pos.x
		return internal_proc(patt(s,pos),start,pos,proc,errproc)
	@cacheall
	def proc(patt,proc,errproc=None):
		#@cacheread
		@functools.wraps(patt)
		def r_proc(s,pos):
			return read_proc(s,pos, patt,proc,errproc)
		return cacheread(r_proc) if errproc!=None else r_proc
	global_proc = proc

'''
функции типа                функция(s,pos,...) - записываются с префиксом read_
переменные типа             функция(s,pos)     - записываются как есть
функции, которые возвращают функцию(s,pos)     - записываются как есть
если возникет конфликт имён у предыдущих двух случаев, то переменная записывается с префиксом r_

для дальнейшего кэширования функции должны возвращать immutable объект
есть альтернатива: прикэшировании и возвращения из кэшированного делать deepcopy объекта

общие соглашения для функций:
если функция возвращает ParseError, то она должна восстановить pos.x на start
Если функция от кого-то получила ProcError,
	то она дальше всё парсит в обычном порядке, но ничего не обрабатывает. И возвращает полученный ProcError
Если функция хочет вернуть ProcWarning, то она должна прогнать его через internal_proc

общие соглашения для обработчиков:
можно вернуть ProcError
можно результат обернуть в ProcWarning
а если надо инициировать фатальную ошибку, то можно вернуть ParseError(-1,...)
??? если proc() вернул ParseError , будет ли он обрабатываться errproc() ???

для обработчиков функции atleast_oneof формат результатов и аргументов обработчиков свой
'''
if 1: # charset str regexp
	@cacheall
	def char_in_set(st,proc=None,errproc=None):
		expected = "@#$ oneof r'"+st+"'"
		# если вызываешь proc/global_proc, то здесь кэшировать не надо
		def r_char_in_set(s,pos):
			if pos.x==len(s):
				return ParseError(pos.x,expected)
			if (r:=s[pos.x]) in st:
				pos.x+=1
				return r
			else:
				return ParseError(pos.x,expected)
		return global_proc(r_char_in_set,proc,errproc)
	@cacheall
	def char_not_in_set(st,proc=None,errproc=None):
		expected = "@#$ not oneof r'"+st+"'"
		# если вызываешь proc/global_proc, то здесь кэшировать не надо
		def r_char_not_in_set(s,pos):
			if pos.x==len(s):
				return ParseError(pos.x,expected)
			if (r:=s[pos.x]) not in st:
				pos.x+=1
				return r
			else:
				return ParseError(pos.x,expected)
		return global_proc(r_char_not_in_set,proc,errproc)
	@cacheall
	def fix_str(st):
		def r_fix_str(s,pos):
			if pos.x+len(st) > len(s):
				return ParseError(pos.x,st)
			if s[pos.x:pos.x+len(st)] == st:
				pos.x+=len(st)
				return st
			else:
				return ParseError(pos.x,st)
		return r_fix_str
	@cacheall
	def regexp(patt,proc=None,errproc=None):
		'''proc получает на вход match-объект целиком, а без обработки возвращает просто строку'''
		pattern = re.compile(patt)
		expected = "@#$ re "+repr(patt)
		# если вызываешь proc/global_proc, то здесь кэшировать не надо
		def r_regexp(s,pos):
			if (r:=pattern.match(s[pos.x:])):
				pos.x+=r.end()
				return r
			else:
				return ParseError(pos.x,expected)
		return global_proc(r_regexp,proc if proc!=None else lambda r:r[0]   ,errproc)
	def read_end_of_stream(s,pos):
			if pos.x==len(s):
				return True
			else:
				return ParseError(pos.x,'end of stream')
	end_of_stream = read_end_of_stream

if 1: # sequence
	def read_sequential(s,pos,/,**read_smth):
		'''
		A B C
		read_smth имеет формат name=func(s,pos) или name=str, 
		а также в нём могут встречаться proc=func(result) и errproc=func(start,err)
		к результату errproc в начале автоматически добавится ('err',
		'''
		# after python 3.6 read_smth will preserve order of arguments
		if 'proc' in read_smth:
			proc = read_smth['proc']
			del read_smth['proc']
		else:
			proc = None
		if 'errproc' in read_smth:
			errproc = read_smth['errproc']
			del read_smth['errproc']
		else:
			errproc = None

		rr = OrderedDict()
		start = pos.x
		has_proc_err = None
		for name,fun in read_smth.items():
			#print(name) # enshure that it really preserve order of arguments
			if type(fun)==str: ## todo убрать преобразования строк в read_fix_str из read_* функций в создающие
				fun = fix_str(fun)

			if isok(r:=fun(s,pos)):
				rr[name]=r
				if isinstance(r,ProcError):
					has_proc_err = r
			else:
				pos.x = start
				r = ParseError(pos.x,'@#$ some sequence',r)
				return internal_proc(r,start,pos,None,errproc) # (r,start,pos,proc,errproc)
		if not (has_proc_err is None):
			return has_proc_err
		else:
			return internal_proc(FrozenAttrOrderedDict(rr),start,pos,proc,errproc)
	@cacheall
	def sequential(**read_smth):
		#@cacheread
		def seq(s,pos):
			return read_sequential(s,pos,**read_smth)
		return cacheread(seq) if 'errproc' in read_smth else seq
	read_sequence = read_sequential
	sequence = sequential

if 1: # oneof
	def read_oneof(s,pos,*read_smth,proc=None,errproc=None):
		'''
		A|B|C
		параметры могут быть функциями или строками
		'''
		errs = []
		rr = []
		start = pos.x
		for fun in read_smth:
			if type(fun)==str: ## todo убрать преобразования строк в read_fix_str из read_* функций в создающие
				fun = fix_str(fun)
			if isok(r:=fun(s,pos)):
				rr.append((r,pos.x))
				pos.x = start
			else:
				assert pos.x==start , 'if function return ParseError, it should restore pos'
				errs.append(r)
		if len(rr)==0:
			return internal_proc(ParseError(pos.x,'@#$ one of',tuple(errs)),start,pos,proc,errproc)
		elif len(rr)==1:
			pos.x = rr[0][1]
			return internal_proc(rr[0][0],start,pos,proc,errproc)
		else:
			raise ValueError((pos.x,'ambiguous results ',rr))
	@cacheall
	def oneof(*read_smth,proc=None,errproc=None):
		#@cacheread
		def r_oneof(s,pos):
			return read_oneof(s,pos,*read_smth,proc=proc,errproc=errproc)
		return cacheread(r_oneof) if errproc!=None else r_oneof

	def read_atleast_oneof(s,pos,**read_smth):
		'''
		A|B|C
		параметры могут быть функциями или строками
		обработчик должен принимать список пар (результат, позиция окончания)
		обрабатывать это и возвращать только одну пару (результат, позиция окончания)
		взвращает список результатов ## todo улучшить интерфейс
		'''
		if 'proc' in read_smth:
			proc = read_smth['proc']
			del read_smth['proc']
		else:
			proc = None
		if 'errproc' in read_smth:
			errproc = read_smth['errproc']
			del read_smth['errproc']
		else:
			errproc = None

		rr = {}
		errs = {}
		start = pos.x
		for name,fun in read_smth.items():
			#print(name) # enshure that it really preserve order of arguments
			if type(fun)==str: ## todo убрать преобразования строк в read_fix_str из read_* функций в создающие
				fun = fix_str(fun)

			if isok(r:=fun(s,pos)):
				rr[name]=(r,pos.x)
				pos.x = start
			else:
				assert pos.x==start , 'if function return ParseError, it should restore pos'
				errs[name] = r
		if len(rr)==0:
			return internal_proc(ParseError(pos.x,'@#$ at least one of',FrozenAttrDict(errs)),start,pos,proc,errproc)
		else:
			res = internal_proc(FrozenAttrDict(rr),start,pos,proc,errproc)
			if isok(res):
				rr,pos.x = res
			else:
				rr = res
			return rr # - this is processed result, ^proc here up
	@cacheall
	def atleast_oneof(**read_smth):
		#@cacheread
		def r_atleast_oneof(s,pos):
			return read_atleast_oneof(s,pos,**read_smth)
		return cacheread(r_atleast_oneof) if 'errproc' in read_smth else r_atleast_oneof

if 1: # repeatedly optional
	infinity = float('inf')
	def read_repeatedly(s,pos,min,max,patt,proc=None,errproc=None): # posessive
		'''
		patt{min,max} # пытается прочитать как можно больше паттернов
		'''
		rr = []
		i=0
		start = pos.x
		has_proc_err = None
		while i<min:
			if isok(r:=patt(s,pos)):
				rr.append(r)
				i+=1
				if isinstance(r,ProcError):
					has_proc_err = r
			else:
				pos.x = start
				return internal_proc(r,start,pos,proc,errproc) # it is error
		cur = -1
		while i<max and isok(r:=patt(s,pos)):
			if pos.x==cur and max==infinity : raise Exception('infinity loop')
			cur = pos.x
			rr.append(r)
			i+=1
			if isinstance(r,ProcError):
				has_proc_err = r
		if not (has_proc_err is None):
			return has_proc_err
		else:
			return internal_proc(tuple(rr),start,pos,proc,errproc)
	@cacheall
	def repeatedly(min,max,patt,proc=None,errproc=None):
		#@cacheread
		def rep(s,pos):
			return read_repeatedly(s,pos,min,max,patt,proc,errproc)
		return cacheread(rep) if errproc!=None else rep
	def read_optional(s,pos,patt):
		'''A?'''
		return read_repeatedly(s,pos,0,1,patt)
	rep_star = lambda patt,proc=None,errproc=None : repeatedly(0,infinity,patt,proc,errproc)
	rep_plus = lambda patt,proc=None,errproc=None : repeatedly(1,infinity,patt,proc,errproc)

	def read_repeatedly_sep(s,pos,min,max,patt,sep,proc,errproc): # posessive
		'''
		patt?(sep patt){min-1,max-1} # если min==0
		patt(sep patt){min-1,max-1} # если min>0
		'''
		rr = []
		i=0
		start = pos.x
		has_proc_err = None
		if isok(r:=patt(s,pos)):
			rr.append(r)
			i+=1
			if isinstance(r,ProcError):
				has_proc_err = r
		else:
			if min==0:
				return internal_proc([],start,pos,proc,errproc)
			else:
				assert start==pos.x , 'if function return ParseError, it should restore pos'
				return internal_proc(r,start,pos,proc,errproc) # it is error
		while i<min:
			if not isok(r:=sep(s,pos)):
				return internal_proc(r,start,pos,proc,errproc) # it is error
			if isok(r:=patt(s,pos)):
				rr.append(r)
				i+=1
				if isinstance(r,ProcError):
					has_proc_err = r
			else:
				pos.x = start
				return internal_proc(r,start,pos,proc,errproc) # it is error
		while i<max:
			xx = pos.x
			if not isok(sep(s,pos)):
				break
			if not isok(r:=patt(s,pos)):
				pos.x = xx
				break
			rr.append(r)
			if isinstance(r,ProcError):
				has_proc_err = r
			i+=1
		if not (has_proc_err is None):
			return has_proc_err
		else:
			return internal_proc(tuple(rr),start,pos,proc,errproc)
	def read_repeatedly_sep_opt(s,pos,min,max,patt,sep,proc,errproc): # posessive
		'''
		patt?(sep patt){min-1,max-1}sep? # если min==0
		patt(sep patt){min-1,max-1}sep?  # если min>0
		'''
		rr = []
		i=0
		start = pos.x
		has_proc_err = None
		if isok(r:=patt(s,pos)):
			rr.append(r)
			i+=1
			if isinstance(r,ProcError):
				has_proc_err = r
		else:
			if min==0:
				return internal_proc([],start,pos,proc,errproc)
			else:
				assert start==pos.x , 'if function return ParseError, it should restore pos'
				return internal_proc(r,start,pos,proc,errproc) # it is error
		while i<min:
			if not isok(r:=sep(s,pos)):
				return internal_proc(r,start,pos,proc,errproc) # it is error
			if isok(r:=patt(s,pos)):
				rr.append(r)
				i+=1
				if isinstance(r,ProcError):
					has_proc_err = r
			else:
				pos.x = start
				return internal_proc(r,start,pos,proc,errproc) # it is error
		while i<max:
			xx = pos.x
			if not isok(sep(s,pos)):
				break
			if not isok(r:=patt(s,pos)):
				pos.x = xx
				break
			rr.append(r)
			if isinstance(r,ProcError):
				has_proc_err = r
			i+=1
		if not (has_proc_err is None):
			return has_proc_err
		else:
			return internal_proc(tuple(rr),start,pos,proc,errproc)

	def read_repeatedly_until(s,pos,patt,patt_stop,proc,errproc):
		'''
		patt*patt_stop # прекращает парсить сразу как только получилось прочитать patt2
		результат patt_stop добавляет в конец массива результатов patt*
		'''
		start = pos.x
		rr = []
		cur = -1
		while True:
			if pos.x==cur : raise Exception('infinity loop')
			cur = pos.x
			if isok(rs:=patt_stop(s,pos)):
				rr.append(rs)
				return internal_proc(tuple(rr),start,pos,proc,errproc)
			else:
				pos.x = cur
				if isok(r:=patt(s,pos)):
					rr.append(r)
				else:
					pos.x = start
					return ParseError(start,'@#$ repeatedly until',(r,rs))
	@cacheall
	def repeatedly_until(patt,patt_stop,proc=None,errproc=None):
		#@cacheread
		def repu(s,pos):
			return read_repeatedly_until(s,pos,patt,patt_stop,proc,errproc)
		return cacheread(repu) if errproc!=None else repu

if 1: # some common processors
	lcat = lambda l : ''.join(l)
	dcat = lambda d : ''.join(v for k,v in d.items())
	def lcatf(proc):
		return lambda l : proc(''.join(l))
	def dcatf(proc):
		return lambda d : proc(''.join(v for k,v in d.items()))
	inthex = lambda x : int(x,16)
	intoct = lambda x : int(x,8)
	def dflt(v):
		return lambda x : x[0] if len(x)==1 else v

	optional= lambda patt,proc=None,errproc=None : repeatedly(0,1,patt,proc,errproc)
	opt_des = lambda patt : optional(patt,proc=dflt('')) # default empty string
	rep_cat = lambda min,max,patt : repeatedly(min,max,patt, proc=lcat)
	rep_plus_cat = lambda patt : rep_cat(1,infinity,patt)
	rep_star_cat = lambda patt : rep_cat(0,infinity,patt)
	seq_cat = lambda **kvargs : sequential(**kvargs,proc=dcat)

	def select_longest(dict_pairs):
		'длины [1 3 5] - OK->5; [1 1 3] - неоднозначность'
		rr=None
		pp=-1
		for name,(r,p) in dict_pairs.items():
			if p>pp:
				pp=p
				rr=r
			elif p==pp:
				raise ValueError('ambiguous results with same length',r,p,rr,pp)
		return (rr,pp)
	def filter_not(dict_pairs):
		for name in dict_pairs:
			if name.startswith('not'):
				return ParseError(-1,'@#$ not')
		return dict_pairs

	def compose(*funs):
		def fun(r):
			for f in reversed(funs):
				if isinstance(r,ParseError) or isinstance(r,ProcError):
					return r
				elif isinstance(r,ProcWarning):
					raise NotImplementedException()
				r=f(r)
			return r
		return fun
	def dict_append(d,**kvargs):
		return FrozenAttrDict(d|kvargs)
	def dict_delete(d,**kvargs):
		return FrozenAttrDict({k:v for k,v in d.items() if k not in kvargs})
