import os
import re
import functools
from collections import OrderedDict
import doctest

'''
ошибкой считается тупл у которого первый элемент 'err'
'''
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

CACHING_ENABLED = True
cacheall = lambda x : functools.cache(x) if CACHING_ENABLED else x
def cacheread(func):
    if not CACHING_ENABLED:
        return func
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
    return wrapper
    
class OrderedAttrDict(OrderedDict):
    def __getattr__(self, key):
        return self[key]
    def __setattr__(self, key, value):
        self[key] = value
def mkodict(**kwargs):
    print(type(kwargs))
    return OrderedAttrDict(kwargs)
class AttrDict(dict):
    def __getattr__(self, key):
        return self[key]
    def __setattr__(self, key, value):
        self[key] = value
def mkdict(**kwargs):
    return AttrDict(kwargs)
def mkpos(x):
    return mkdict(x=x)

'''
функции типа                функция(s,pos,...) - записываются с префиксом read_
переменные типа             функция(s,pos)     - записываются как есть
функции, которые возвращают функцию(s,pos)     - записываются как есть
если возникет конфликт имён у предыдущих двух случаев, то переменная записывается с префиксом r_
'''
@cacheall
def read(s,pos,patt):
    '''
    fun(params)(s,pos) мы заменяем на
    read(s,pos,fun(params)) 
    '''
    return patt(s,pos)
def internal_proc(r,proc,errproc):
    if isok(r):
        if proc!=None:
            r = proc(r)
    else:
        if errproc!=None:
            if type(errproc) is str:
                r.chname(errproc)
            else:
                r= errproc(r)
    return r
def read_proc(s,pos,patt,proc,errproc=None):
    return internal_proc(patt(s,pos),proc,errproc)
@cacheall
def proc(patt,proc,errproc=None):
    @cacheread
    def r_proc(s,pos):
        return read_proc(s,pos, patt,proc,errproc)
    return r_proc
global_proc = proc
    
@cacheall
def char_in_set(st,proc=None,errproc=None):
    expected = "oneof r'"+st+"'"
    @cacheread
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
    expected = "re r'"+patt+"'"
    @cacheread
    def r_regexp(s,pos):
        if (r:=pattern.match(s[pos.x:])):
            pos.x+=r.end()
            return r
        else:
            return ParseError(pos.x,expected)
    return global_proc(r_regexp,proc if proc!=None else lambda r:r[0]   ,errproc)

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
    for name,fun in read_smth.items():
        #print(name) # enshure that it really preserve order of arguments
        if type(fun)==str:
            fun = fix_str(fun)
            
        if isok(r:=fun(s,pos)):
            rr[name]=r
        else:
            r.expected(start,'some sequence')
            return internal_proc(r,None,errproc)
    return internal_proc(OrderedAttrDict(rr),proc,errproc)
@cacheall
def sequential(**read_smth):
    @cacheread
    def seq(s,pos):
        return read_sequential(s,pos,**read_smth)
    return seq
    
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
            errs.append(r)
    if len(rr)==0:
        return internal_proc(ParseError(pos.x,'one of',errs),proc,errproc)
    elif len(rr)==1:
        pos.x = rr[0][1]
        return internal_proc(rr[0][0],proc,errproc)
    else:
        raise ValueError((pos.x,'ambiguous results ',rr))
@cacheall
def oneof(*read_smth):
    @cacheread
    def r_oneof(s,pos):
        return read_oneof(s,pos,*read_smth)
    return r_oneof
    

infinity = float('inf')
def read_repeatedly(s,pos,min,max,patt,proc=None,errproc=None): # posessive
    '''
    patt{min,max} # пытается прочитать как можно больше паттернов
    '''
    rr = []
    i=0
    while i<min:
        if isok(r:=patt(s,pos)):
            rr.append(r)
            i+=1
        else:
            return r # it is error
    while i<max and isok(r:=patt(s,pos)):
        rr.append(r)
        i+=1
    return internal_proc(rr,proc,errproc)
@cacheall
def repeatedly(min,max,patt,proc=None,errproc=None):
    @cacheread
    def rep(s,pos):
        return read_repeatedly(s,pos,min,max,patt,proc,errproc)
    return rep
    
def read_optional(s,pos,patt):
    '''A?'''
    return read_repetedly(s,pos,0,1,patt)
def read_repeatedly_sep(s,pos,min,max,patt,sep): # posessive
    '''
    patt?(sep patt){min-1,max-1} # если min==0
    patt(sep patt){min-1,max-1} # если min>0
    '''
    rr = []
    i=0
    if isok(r:=patt(s,pos)):
        rr.append(r)
        i+=1
    else:
        if min==0:
            return []
        else:
            return r # it is error
    while i<min:
        if not isok(r:=sep(s,pos)):
            return r
        if isok(r:=patt(s,pos)):
            rr.append(r)
            i+=1
        else:
            return r # it is error
    while i<max:
        xx = pos.x
        if not isok(sep(s,pos)):
            break
        if not isok(r:=patt(s,pos)):
            pos.x = xx
            break
        rr.append(r)
        i+=1
    return rr
def read_repeatedly_sep_opt(s,pos,min,max,patt,sep): # posessive
    '''
    patt?(sep patt){min-1,max-1}sep? # если min==0
    patt(sep patt){min-1,max-1}sep?  # если min>0
    '''
    rr = []
    i=0
    if isok(r:=patt(s,pos)):
        rr.append(r)
        i+=1
    else:
        if min==0:
            return []
        else:
            return r
    while i<min:
        if not isok(r:=sep(s,pos)):
            return r
        if isok(r:=patt(s,pos)):
            rr.append(r)
            i+=1
        else:
            return r
    while i<max:
        xx = pos.x
        if not isok(sep(s,pos)):
            break
        if not isok(r:=patt(s,pos)):
            pos.x = xx
            break
        rr.append(r)
        i+=1
    return rr
def read_repeatedly_further(s,pos,min,max,patt1,patt2):
    '''
    patt1{min,max}patt2 # прекращает парсить сразу как только получилось прочитать patt2
    '''
    pass