import re
import functools
from collections import OrderedDict
import doctest

# attr ordered dict
if 1: # just for folding
    class AttrOrderedDict(OrderedDict):
        def __getattr__(self, key):
            if key not in self:
                raise AttributeError()
            return self[key]
        def __setattr__(self, key, value):
            self[key] = value
        def __repr__(self):
            return 'mkodict('+', '.join(k+'='+repr(v) for k,v in self.items())+')' # если встретиться ключ, который не является строкой, то будет исключение
    def mkodict(**kwargs):
        return AttrOrderedDict(kwargs)
    class AttrDict(dict):
        def __getattr__(self, key):
            if key not in self:
                raise AttributeError()
            return self[key]
        def __setattr__(self, key, value):
            self[key] = value
        def __repr__(self):
            return 'mkdict('+', '.join(k+'='+repr(v) for k,v in self.items())+')' # если встретиться ключ, который не является строкой, то будет исключение
    def mkdict(**kwargs):
        return AttrDict(kwargs)
    def mkpos(x):
        return mkdict(x=x)

# error classes
if 1: # just for folding
    class ParseError: # it is not exception
        __slots__ = ['what','details']
        def __init__(self,pos,expected,details=None):
            self.what = [(pos,expected)] # список где и какой паттерн ожидался
                                        # при выводе сообщений 'expected ' будет добаляться автоматически (expected!=None)
            self.details = details # как правило создается в oneof
                                    # также сюда более сложные сообщения
        def expected(self,pos,expected):
            self.what.append((pos,expected))
            return self
        def chname(self,expected):
            '''заменяет expected  в последней причине'''
            self.what[-1] = (self.what[-1][0],expected)
            return self
        def __repr__(self):
            return 'parseError'+repr(([x for x in reversed(self.what)],self.details))
    def parseError(what,details):
        '''
        >>> parseError([(0, 'one of')], [parseError([(0, '0x')], None), parseError([(0, '0X')], None)])
        parseError([(0, 'one of')], [parseError([(0, '0x')], None), parseError([(0, '0X')], None)])
        '''
        x = ParseError(0,'')
        x.what = [x for x in reversed(what)]
        x.details = details
        return x
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

# debug decorator
if 1: # just for folding
    DEBUGGING = False
    DEBUG_DEPTH = 0
    def debug_start(s,pos,name):
        pref = '\t'*DEBUG_DEPTH
        print(pref,s,sep='')
        print(pref,' '*pos.x,'^-',name,sep='')
    def debug_end(s,start,pos,name,result):
        pref = '\t'*DEBUG_DEPTH
        print(pref,s,sep='')
        if start==pos.x:
            print(pref,' '*start,'V=',result,sep='')
        else:
            print(pref,' '*start,'\\',' '*(pos.x-start-1),'/=',result,sep='')
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

# cache decorator
if 1: # just for folding
    CACHING_ENABLED = False
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
            if s is not ref_s:
                ref_s = s
                memo = {}
            # add the new key to dict if it doesn't exist already  
            start = pos.x
            if start not in memo:
                r = func(s,pos)
                stop = pos.x
                memo[start] = (r,stop)
            pos.x = memo[start][1]
            return memo[start][0]
        return debug(wrapper,func.__name__)

# read proc
if 1: # just for folding
    ERRORS = {}
    WARNINGS = {}
    # индексируются парами (начало, конец) разобранного паттерна
    def reset_errors_warnings():
        global ERRORS, WARNINGS
        ERRORS = {}
        WARNINGS = {}
    def get_errors_warnings():
        return (ERRORS, WARNINGS)
    PROC_DEBUG = False
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
                    r.chname(errproc)
                else:
                    r= errproc(r)
        return r
    def read_proc(s,pos,patt,proc,errproc=None):
        start = pos.x
        return internal_proc(patt(s,pos),start,pos,proc,errproc)
    @cacheall
    def proc(patt,proc,errproc=None):
        @cacheread
        def r_proc(s,pos):
            return read_proc(s,pos, patt,proc,errproc)
        return r_proc
    global_proc = proc

'''
функции типа                функция(s,pos,...) - записываются с префиксом read_
переменные типа             функция(s,pos)     - записываются как есть
функции, которые возвращают функцию(s,pos)     - записываются как есть
если возникет конфликт имён у предыдущих двух случаев, то переменная записывается с префиксом r_
'''
# charset str regexp        
if 1: # just for folding
    @cacheall
    def char_in_set(st,proc=None,errproc=None):
        expected = "oneof r'"+st+"'"
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
        expected = "re "+repr(patt)
        # если вызываешь proc/global_proc, то здесь кэшировать не надо
        def r_regexp(s,pos):
            if (r:=pattern.match(s[pos.x:])):
                pos.x+=r.end()
                return r
            else:
                return ParseError(pos.x,expected)
        return global_proc(r_regexp,proc if proc!=None else lambda r:r[0]   ,errproc)

# sequence
if 1: # just for folding
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
            if type(fun)==str:
                fun = fix_str(fun)
                
            if isok(r:=fun(s,pos)):
                rr[name]=r
                if isinstance(r,ProcError):
                    has_proc_err = r
            else:
                pos.x = start
                r.expected(pos.x,'some sequence')
                return internal_proc(r,None,start,pos,errproc)
        if not (has_proc_err is None):
            return has_proc_err
        else:
            return internal_proc(AttrOrderedDict(rr),start,pos,proc,errproc)
    @cacheall
    def sequential(**read_smth):
        @cacheread
        def seq(s,pos):
            return read_sequential(s,pos,**read_smth)
        return seq
    read_sequence = read_sequential
    sequence = sequential

# oneof
if 1: # just for folding
    def read_oneof(s,pos,*read_smth,proc=None,errproc=None):
        '''
        A|B|C
        параметры могут быть функциями или строками
        '''
        errs = []
        rr = []
        start = pos.x
        for fun in read_smth:
            if type(fun)==str:
                fun = fix_str(fun)
            if isok(r:=fun(s,pos)):
                rr.append((r,pos.x))
                pos.x = start
            else:
                assert pos.x==start
                errs.append(r)
        if len(rr)==0:
            return internal_proc(ParseError(pos.x,'one of',errs),start,pos,proc,errproc)
        elif len(rr)==1:
            pos.x = rr[0][1]
            return internal_proc(rr[0][0],start,pos,proc,errproc)
        else:
            raise ValueError((pos.x,'ambiguous results ',rr))
    @cacheall
    def oneof(*read_smth,proc=None,errproc=None):
        @cacheread
        def r_oneof(s,pos):
            return read_oneof(s,pos,*read_smth,proc=proc,errproc=errproc)
        return r_oneof
        
    def read_atleast_oneof(s,pos,*read_smth,proc,errproc=None):
        '''
        A|B|C
        параметры могут быть функциями или строками
        обработчик должен принимать список пар (результат, позиция окончания)
        обрабатывать это и возвращать только одну пару (результат, позиция окончания)
        '''
        errs = []
        rr = []
        start = pos.x
        for fun in read_smth:
            if type(fun)==str:
                fun = fix_str(fun)
            if isok(r:=fun(s,pos)):
                rr.append((r,pos.x))
                pos.x = start
            else:
                assert pos.x==start
                errs.append(r)
        if len(rr)==0:
            return internal_proc(ParseError(pos.x,'one of',errs),start,pos,proc,errproc)
        else:
            rr,pos.x = internal_proc(rr,start,pos,proc,errproc)
            return rr #^proc here up
    @cacheall
    def atleast_oneof(*read_smth,proc,errproc=None):
        @cacheread
        def r_atleast_oneof(s,pos):
            return read_atleast_oneof(s,pos,*read_smth,proc=proc,errproc=errproc)
        return r_atleast_oneof
        
# repeatedly optional
if 1: # just for folding
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
        while i<max and isok(r:=patt(s,pos)):
            rr.append(r)
            i+=1
            if isinstance(r,ProcError):
                has_proc_err = r
        if not (has_proc_err is None):
            return has_proc_err
        else:
            return internal_proc(rr,start,pos,proc,errproc)
    @cacheall
    def repeatedly(min,max,patt,proc=None,errproc=None):
        @cacheread
        def rep(s,pos):
            return read_repeatedly(s,pos,min,max,patt,proc,errproc)
        return rep
    def read_optional(s,pos,patt):
        '''A?'''
        return read_repetedly(s,pos,0,1,patt)
        
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
                assert start==pos.x
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
            return internal_proc(rr,start,pos,proc,errproc)
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
                assert start==pos.x
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
            return internal_proc(rr,start,pos,proc,errproc)
    def read_repeatedly_further(s,pos,min,max,patt1,patt2):
        '''
        patt1{min,max}patt2 # прекращает парсить сразу как только получилось прочитать patt2
        '''
        raise NotImplementedError()

# some common processors
if 1: # just for folding
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
    seq_cat = lambda **kvargs : sequential(**kvargs,proc=dcat)

    def select_longest(lp):
        rr=None
        pp=-1
        for r,p in lp:
            if p>pp:
                pp=p
                rr=r
            elif p==pp:
                raise ValueError('ambiguous results with same length',r,p,rr,pp)
        return (rr,pp)
    def compose(*funs):
        def fun(r):
            for f in reversed(funs):
                r=f(r)
            return r
        return fun
    def dict_append(d,**kvargs):
        for k,v in kvargs.items():
            d[k]=v
        return d
    def dict_delete(d,**kvargs):
        for k,v in kvargs.items():
            del d[k]
        return d