#!/usr/bin/env python3
"""
gen_batches.py  —  creates batches/batch_02 through batches/batch_05
Each batch has 10 projects with src/*.c, diff.txt, ground_truth.json.
Diffs are generated via difflib so line numbers are always exact.

Usage (from project root):
    python scripts/gen_batches.py
"""
import os, json, difflib

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def make_diff(before: str, after: str, filename: str) -> str:
    bl = before.splitlines(keepends=True)
    al = after.splitlines(keepends=True)
    lines = list(difflib.unified_diff(bl, al,
        fromfile=f"a/src/{filename}", tofile=f"b/src/{filename}", n=3))
    if not lines:
        return ""
    hdr = f"diff --git a/src/{filename} b/src/{filename}\nindex abc1234..def5678 100644\n"
    return hdr + "".join(lines)

def create(proj: dict):
    bd = os.path.join(ROOT, "batches", f"batch_{proj['batch']}", proj['name'])
    sd = os.path.join(bd, "src")
    os.makedirs(sd, exist_ok=True)
    diffs = []
    for fname, (before, after) in proj['files'].items():
        with open(os.path.join(sd, fname), "w") as f:
            f.write(after)
        d = make_diff(before, after, fname)
        if d:
            diffs.append(d)
    with open(os.path.join(bd, "diff.txt"), "w") as f:
        f.write("\n".join(diffs))
    with open(os.path.join(bd, "ground_truth.json"), "w") as f:
        json.dump(proj['truth'], f, indent=2)
    print(f"  batch_{proj['batch']}/{proj['name']}")

# ---------------------------------------------------------------------------
# Project definitions  (before, after)  — after is the fixed/correct version
# ---------------------------------------------------------------------------
PROJECTS = []

# ═══════════════════════════════════════════════════════════════════════════
# BATCH 02
# ═══════════════════════════════════════════════════════════════════════════

# 02/01 — timer: overflow guard added to timer_elapsed
_t = r"""#include <stdio.h>
typedef unsigned int uint;
typedef struct { uint start; uint end; } Timer;
void timer_start(Timer *t, uint now) { t->start = now; }
uint timer_elapsed(Timer *t, uint now) {
    return now - t->start;
}
void timer_stop(Timer *t, uint now) { t->end = now; }
uint timer_duration(Timer *t) { return t->end - t->start; }
int main(void) {
    Timer t;
    timer_start(&t, 100);
    uint e = timer_elapsed(&t, 200);
    timer_stop(&t, 200);
    printf("%u %u\n", e, timer_duration(&t));
    return 0;
}
"""
PROJECTS.append({"batch":"02","name":"01_timer","files":{"timer.c":(
    _t,
    _t.replace(
        "    return now - t->start;\n",
        "    if (now < t->start) return 0;\n    return now - t->start;\n")
)},"truth":{"all_functions":["main","timer_duration","timer_elapsed","timer_start","timer_stop"],
           "changed_functions":["timer_elapsed"],"affected_functions":["main"]}})

# 02/02 — counter: underflow guard added to counter_dec
_c = r"""#include <stdio.h>
typedef struct { int val; int min; int max; } Counter;
void counter_init(Counter *c, int mn, int mx) { c->val=0; c->min=mn; c->max=mx; }
void counter_inc(Counter *c) { if (c->val < c->max) c->val++; }
void counter_dec(Counter *c) {
    c->val--;
}
int counter_get(Counter *c) { return c->val; }
void counter_reset(Counter *c) { c->val = 0; }
int main(void) {
    Counter c; counter_init(&c, 0, 5);
    counter_inc(&c); counter_dec(&c);
    printf("%d\n", counter_get(&c));
    return 0;
}
"""
PROJECTS.append({"batch":"02","name":"02_counter","files":{"counter.c":(
    _c,
    _c.replace(
        "void counter_dec(Counter *c) {\n    c->val--;\n}",
        "void counter_dec(Counter *c) {\n    if (c->val <= c->min) return;\n    c->val--;\n}")
)},"truth":{"all_functions":["counter_dec","counter_get","counter_inc","counter_init","counter_reset","main"],
           "changed_functions":["counter_dec"],"affected_functions":["main"]}})

# 02/03 — minmax: sentinel init fixed in find_min and find_max
_mm_before = r"""#include <stdio.h>
#include <limits.h>
int find_min(int *a, int n) {
    int m = INT_MAX;
    for (int i = 0; i < n; i++) if (a[i] < m) m = a[i];
    return m;
}
int find_max(int *a, int n) {
    int m = INT_MIN;
    for (int i = 0; i < n; i++) if (a[i] > m) m = a[i];
    return m;
}
int range(int *a, int n) { return find_max(a,n) - find_min(a,n); }
int main(void) {
    int a[]={3,1,4,1,5};
    printf("min=%d max=%d range=%d\n", find_min(a,5), find_max(a,5), range(a,5));
    return 0;
}
"""
_mm_after = r"""#include <stdio.h>
int find_min(int *a, int n) {
    int m = a[0];
    for (int i = 1; i < n; i++) if (a[i] < m) m = a[i];
    return m;
}
int find_max(int *a, int n) {
    int m = a[0];
    for (int i = 1; i < n; i++) if (a[i] > m) m = a[i];
    return m;
}
int range(int *a, int n) { return find_max(a,n) - find_min(a,n); }
int main(void) {
    int a[]={3,1,4,1,5};
    printf("min=%d max=%d range=%d\n", find_min(a,5), find_max(a,5), range(a,5));
    return 0;
}
"""
PROJECTS.append({"batch":"02","name":"03_minmax","files":{"minmax.c":(_mm_before,_mm_after)},
"truth":{"all_functions":["find_max","find_min","main","range"],
         "changed_functions":["find_max","find_min"],"affected_functions":["main","range"]}})

# 02/04 — checksum: crc8 polynomial fixed
_cs = r"""#include <stdio.h>
unsigned char crc8(unsigned char *data, int len) {
    unsigned char crc = 0xFF;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++)
            crc = (crc & 0x80) ? (unsigned char)((crc<<1)^0x31) : (unsigned char)(crc<<1);
    }
    return crc;
}
int verify(unsigned char *data, int len, unsigned char expected) {
    return crc8(data, len) == expected;
}
int main(void) {
    unsigned char d[]={0x01,0x02,0x03};
    unsigned char c = crc8(d,3);
    printf("crc=%02x valid=%d\n", c, verify(d,3,c));
    return 0;
}
"""
PROJECTS.append({"batch":"02","name":"04_checksum","files":{"checksum.c":(
    _cs,
    _cs.replace("0x31","0x07")
)},"truth":{"all_functions":["crc8","main","verify"],
           "changed_functions":["crc8"],"affected_functions":["main","verify"]}})

# 02/05 — tokenizer: null terminator added to tok_next
_tok = r"""#include <stdio.h>
#include <string.h>
typedef struct { const char *src; int pos; int len; } Tok;
void tok_init(Tok *t, const char *src) { t->src=src; t->pos=0; t->len=strlen(src); }
int tok_next(Tok *t, char *out, int sz) {
    while (t->pos < t->len && t->src[t->pos]==' ') t->pos++;
    if (t->pos >= t->len) return 0;
    int start = t->pos;
    while (t->pos < t->len && t->src[t->pos]!=' ') t->pos++;
    int n = t->pos - start;
    if (n >= sz) n = sz - 1;
    memcpy(out, t->src + start, n);
    return n;
}
int tok_has_more(Tok *t) { return t->pos < t->len; }
int main(void) {
    Tok t; tok_init(&t, "hello world");
    char buf[32];
    while (tok_next(&t, buf, sizeof(buf)))
        printf("[%s]\n", buf);
    return 0;
}
"""
PROJECTS.append({"batch":"02","name":"05_tokenizer","files":{"tokenizer.c":(
    _tok,
    _tok.replace(
        "    memcpy(out, t->src + start, n);\n    return n;",
        "    memcpy(out, t->src + start, n);\n    out[n] = '\\0';\n    return n;")
)},"truth":{"all_functions":["main","tok_has_more","tok_init","tok_next"],
           "changed_functions":["tok_next"],"affected_functions":["main"]}})

# 02/06 — bitset: bs_count fixed (counted words not bits)
_bs_before = r"""#include <stdio.h>
#define WORDS 4
typedef struct { unsigned int w[WORDS]; } Bitset;
void bs_set(Bitset *b, int i) { b->w[i/32] |= 1u<<(i%32); }
void bs_clear(Bitset *b, int i) { b->w[i/32] &= ~(1u<<(i%32)); }
int bs_test(Bitset *b, int i) { return (b->w[i/32]>>(i%32))&1; }
int bs_count(Bitset *b) {
    int n = 0;
    for (int i = 0; i < WORDS; i++)
        if (b->w[i]) n++;
    return n;
}
int main(void) {
    Bitset b = {0};
    bs_set(&b,1); bs_set(&b,5); bs_set(&b,33);
    printf("count=%d\n", bs_count(&b));
    return 0;
}
"""
_bs_after = r"""#include <stdio.h>
#define WORDS 4
typedef struct { unsigned int w[WORDS]; } Bitset;
void bs_set(Bitset *b, int i) { b->w[i/32] |= 1u<<(i%32); }
void bs_clear(Bitset *b, int i) { b->w[i/32] &= ~(1u<<(i%32)); }
int bs_test(Bitset *b, int i) { return (b->w[i/32]>>(i%32))&1; }
int bs_count(Bitset *b) {
    int n = 0;
    for (int i = 0; i < WORDS; i++) {
        unsigned int w = b->w[i];
        while (w) { n += w&1; w>>=1; }
    }
    return n;
}
int main(void) {
    Bitset b = {0};
    bs_set(&b,1); bs_set(&b,5); bs_set(&b,33);
    printf("count=%d\n", bs_count(&b));
    return 0;
}
"""
PROJECTS.append({"batch":"02","name":"06_bitset","files":{"bitset.c":(_bs_before,_bs_after)},
"truth":{"all_functions":["bs_clear","bs_count","bs_set","bs_test","main"],
         "changed_functions":["bs_count"],"affected_functions":["main"]}})

# 02/07 — search: find_substr off-by-one fixed
_ss = r"""#include <stdio.h>
#include <string.h>
int find_char(const char *s, char c) {
    for (int i=0; s[i]; i++) if (s[i]==c) return i;
    return -1;
}
int find_substr(const char *hay, const char *needle) {
    int hn=strlen(hay), nn=strlen(needle);
    for (int i=0; i < hn-nn; i++)
        if (memcmp(hay+i, needle, nn)==0) return i;
    return -1;
}
int count_occur(const char *hay, const char *needle) {
    int count=0, nn=strlen(needle);
    for (int i=0; i<=(int)strlen(hay)-(int)nn; ) {
        int p = find_substr(hay+i, needle);
        if (p<0) break;
        count++; i+=p+nn;
    }
    return count;
}
int main(void) {
    printf("%d %d\n", find_substr("hello","lo"), count_occur("abab","ab"));
    return 0;
}
"""
PROJECTS.append({"batch":"02","name":"07_search","files":{"search.c":(
    _ss,
    _ss.replace("i < hn-nn","i <= hn-nn")
)},"truth":{"all_functions":["count_occur","find_char","find_substr","main"],
           "changed_functions":["find_substr"],"affected_functions":["count_occur","main"]}})

# 02/08 — stats: variance population fix
_st = r"""#include <stdio.h>
double mean(double *a, int n) {
    double s=0; for(int i=0;i<n;i++) s+=a[i]; return s/n;
}
double variance(double *a, int n) {
    double m=mean(a,n), s=0;
    for(int i=0;i<n;i++){double d=a[i]-m; s+=d*d;}
    return s/(n-1);
}
double stddev(double *a, int n) {
    double v=variance(a,n), r=v;
    for(int i=0;i<20;i++) r=(r+v/r)/2.0;
    return r;
}
int main(void) {
    double a[]={2,4,4,4,5,5,7,9};
    printf("%.3f %.3f\n", variance(a,8), stddev(a,8));
    return 0;
}
"""
PROJECTS.append({"batch":"02","name":"08_stats","files":{"stats.c":(
    _st,
    _st.replace("return s/(n-1);","return s/n;")
)},"truth":{"all_functions":["main","mean","stddev","variance"],
           "changed_functions":["variance"],"affected_functions":["main","stddev"]}})

# 02/09 — moving_avg: guard missing in ma_add
_ma = r"""#include <stdio.h>
#define WIN 4
typedef struct { double buf[WIN]; int pos; int count; double sum; } MovAvg;
void ma_init(MovAvg *m) { m->pos=0; m->count=0; m->sum=0; }
void ma_add(MovAvg *m, double v) {
    m->sum -= m->buf[m->pos];
    m->buf[m->pos] = v;
    m->sum += v;
    m->pos = (m->pos+1)%WIN;
    if (m->count < WIN) m->count++;
}
double ma_get(MovAvg *m) { return m->count>0 ? m->sum/m->count : 0.0; }
int main(void) {
    MovAvg m; ma_init(&m);
    for(int i=1;i<=6;i++){ma_add(&m,i); printf("%.2f\n",ma_get(&m));}
    return 0;
}
"""
PROJECTS.append({"batch":"02","name":"09_moving_avg","files":{"moving_avg.c":(
    _ma,
    _ma.replace(
        "    m->sum -= m->buf[m->pos];\n",
        "    if (m->count == WIN) m->sum -= m->buf[m->pos];\n")
)},"truth":{"all_functions":["ma_add","ma_get","ma_init","main"],
           "changed_functions":["ma_add"],"affected_functions":["main"]}})

# 02/10 — clamp: upper bound missing
_cl = r"""#include <stdio.h>
double clamp(double v, double lo, double hi) {
    if (v < lo) return lo;
    return v;
}
double normalize(double v, double lo, double hi) {
    double c=clamp(v,lo,hi);
    return (hi==lo)?0.0:(c-lo)/(hi-lo);
}
double lerp(double t, double a, double b) {
    return a + clamp(t,0.0,1.0)*(b-a);
}
int main(void) {
    printf("%.2f %.2f %.2f\n", clamp(5.0,0.0,3.0), normalize(5.0,0.0,10.0), lerp(0.5,0.0,10.0));
    return 0;
}
"""
PROJECTS.append({"batch":"02","name":"10_clamp","files":{"clamp.c":(
    _cl,
    _cl.replace(
        "    if (v < lo) return lo;\n    return v;",
        "    if (v < lo) return lo;\n    if (v > hi) return hi;\n    return v;")
)},"truth":{"all_functions":["clamp","lerp","main","normalize"],
           "changed_functions":["clamp"],"affected_functions":["lerp","main","normalize"]}})

# ═══════════════════════════════════════════════════════════════════════════
# BATCH 03
# ═══════════════════════════════════════════════════════════════════════════

# 03/01 — pool: alignment added to pool_alloc
_pl = r"""#include <stdio.h>
#define POOL_SIZE 256
typedef struct { char mem[POOL_SIZE]; int used; } Pool;
void pool_init(Pool *p) { p->used=0; }
void *pool_alloc(Pool *p, int size) {
    if (p->used+size > POOL_SIZE) return 0;
    void *ptr = p->mem + p->used;
    p->used += size;
    return ptr;
}
void pool_reset(Pool *p) { p->used=0; }
int pool_used(Pool *p) { return p->used; }
int main(void) {
    Pool p; pool_init(&p);
    int *a = pool_alloc(&p, sizeof(int));
    *a = 42;
    printf("%d used=%d\n", *a, pool_used(&p));
    pool_reset(&p);
    return 0;
}
"""
PROJECTS.append({"batch":"03","name":"01_pool","files":{"pool.c":(
    _pl,
    _pl.replace(
        "    if (p->used+size > POOL_SIZE) return 0;\n    void *ptr = p->mem + p->used;\n    p->used += size;",
        "    int aligned = (size+3)&~3;\n    if (p->used+aligned > POOL_SIZE) return 0;\n    void *ptr = p->mem + p->used;\n    p->used += aligned;")
)},"truth":{"all_functions":["main","pool_alloc","pool_init","pool_reset","pool_used"],
           "changed_functions":["pool_alloc"],"affected_functions":["main"]}})

# 03/02 — ringbuf2: rb_peek used wrong index
_rb = r"""#include <stdio.h>
#define CAP 8
typedef struct { int d[CAP]; int r,w,n; } RBuf;
void rb_init(RBuf *b) { b->r=b->w=b->n=0; }
int rb_push(RBuf *b, int v) {
    if(b->n>=CAP) return -1;
    b->d[b->w]=v; b->w=(b->w+1)%CAP; b->n++;
    return 0;
}
int rb_pop(RBuf *b, int *out) {
    if(b->n<=0) return -1;
    *out=b->d[b->r]; b->r=(b->r+1)%CAP; b->n--;
    return 0;
}
int rb_peek(RBuf *b, int *out) {
    if(b->n<=0) return -1;
    *out=b->d[b->w];
    return 0;
}
int rb_size(RBuf *b) { return b->n; }
int main(void) {
    RBuf b; rb_init(&b);
    rb_push(&b,1); rb_push(&b,2);
    int v; rb_peek(&b,&v);
    printf("peek=%d size=%d\n",v,rb_size(&b));
    rb_pop(&b,&v); printf("pop=%d\n",v);
    return 0;
}
"""
PROJECTS.append({"batch":"03","name":"02_ringbuf2","files":{"ringbuf.c":(
    _rb,
    _rb.replace("*out=b->d[b->w];","*out=b->d[b->r];")
)},"truth":{"all_functions":["main","rb_init","rb_peek","rb_pop","rb_push","rb_size"],
           "changed_functions":["rb_peek"],"affected_functions":["main"]}})

# 03/03 — hashmap: hm_get missing early-exit on empty slot
_hm = r"""#include <stdio.h>
#include <string.h>
#define HSZ 16
typedef struct { char k[32]; int v; int used; } HME;
typedef struct { HME e[HSZ]; } HMap;
void hm_init(HMap *h) { memset(h,0,sizeof(*h)); }
static int hm_hash(const char *k) {
    unsigned h=0; while(*k) h=h*31+(unsigned char)*k++;
    return h%HSZ;
}
int hm_set(HMap *h, const char *k, int v) {
    int i=hm_hash(k);
    for(int j=0;j<HSZ;j++){
        int idx=(i+j)%HSZ;
        if(!h->e[idx].used||strcmp(h->e[idx].k,k)==0){
            strncpy(h->e[idx].k,k,31); h->e[idx].v=v; h->e[idx].used=1; return 0;
        }
    }
    return -1;
}
int hm_get(HMap *h, const char *k, int *out) {
    int i=hm_hash(k);
    for(int j=0;j<HSZ;j++){
        int idx=(i+j)%HSZ;
        if(strcmp(h->e[idx].k,k)==0){*out=h->e[idx].v; return 0;}
    }
    return -1;
}
int hm_contains(HMap *h, const char *k) { int v; return hm_get(h,k,&v)==0; }
int main(void) {
    HMap h; hm_init(&h);
    hm_set(&h,"x",42); int v; hm_get(&h,"x",&v);
    printf("x=%d has=%d\n",v,hm_contains(&h,"x"));
    return 0;
}
"""
PROJECTS.append({"batch":"03","name":"03_hashmap","files":{"hashmap.c":(
    _hm,
    _hm.replace(
        "        if(strcmp(h->e[idx].k,k)==0){*out=h->e[idx].v; return 0;}",
        "        if(!h->e[idx].used) break;\n        if(strcmp(h->e[idx].k,k)==0){*out=h->e[idx].v; return 0;}")
)},"truth":{"all_functions":["hm_contains","hm_get","hm_hash","hm_init","hm_set","main"],
           "changed_functions":["hm_get"],"affected_functions":["hm_contains","main"]}})

# 03/04 — deque: dq_pop_front missing modulo wrap
_dq = r"""#include <stdio.h>
#define DQCAP 8
typedef struct { int d[DQCAP]; int front,back,n; } Deque;
void dq_init(Deque *q) { q->front=q->back=q->n=0; }
int dq_push_back(Deque *q, int v) {
    if(q->n>=DQCAP) return -1;
    q->d[q->back]=v; q->back=(q->back+1)%DQCAP; q->n++;
    return 0;
}
int dq_pop_front(Deque *q, int *out) {
    if(q->n<=0) return -1;
    *out=q->d[q->front];
    q->front++;
    q->n--;
    return 0;
}
int dq_front(Deque *q, int *out) {
    if(q->n<=0) return -1;
    *out=q->d[q->front]; return 0;
}
int dq_size(Deque *q) { return q->n; }
int main(void) {
    Deque q; dq_init(&q);
    for(int i=0;i<5;i++) dq_push_back(&q,i*10);
    int v; dq_pop_front(&q,&v);
    printf("popped=%d size=%d\n",v,dq_size(&q));
    return 0;
}
"""
PROJECTS.append({"batch":"03","name":"04_deque","files":{"deque.c":(
    _dq,
    _dq.replace("    q->front++;\n","    q->front=(q->front+1)%DQCAP;\n")
)},"truth":{"all_functions":["dq_front","dq_init","dq_pop_front","dq_push_back","dq_size","main"],
           "changed_functions":["dq_pop_front"],"affected_functions":["main"]}})

# 03/05 — prefix_sum: index off-by-one
_ps = r"""#include <stdio.h>
#define PMAX 10
typedef struct { int p[PMAX+1]; int n; } Prefix;
void prefix_build(Prefix *ps, int *arr, int n) {
    ps->n=n; ps->p[0]=0;
    for(int i=0;i<n;i++) ps->p[i]=ps->p[i-1]+arr[i];
}
int prefix_query(Prefix *ps, int l, int r) {
    return ps->p[r+1]-ps->p[l];
}
int prefix_total(Prefix *ps) { return prefix_query(ps,0,ps->n-1); }
int main(void) {
    int a[]={1,2,3,4,5};
    Prefix ps; prefix_build(&ps,a,5);
    printf("sum=%d total=%d\n", prefix_query(&ps,1,3), prefix_total(&ps));
    return 0;
}
"""
PROJECTS.append({"batch":"03","name":"05_prefix_sum","files":{"prefix.c":(
    _ps,
    _ps.replace(
        "    for(int i=0;i<n;i++) ps->p[i]=ps->p[i-1]+arr[i];",
        "    for(int i=0;i<n;i++) ps->p[i+1]=ps->p[i]+arr[i];")
)},"truth":{"all_functions":["main","prefix_build","prefix_query","prefix_total"],
           "changed_functions":["prefix_build"],"affected_functions":["main","prefix_query","prefix_total"]}})

# 03/06 — sliding_window: window_min accumulator not properly tracked
_sw = r"""#include <stdio.h>
int window_min(int *a, int n, int k) {
    int res = a[0];
    for(int i=0; i<=n-k; i++){
        int loc=a[i];
        for(int j=1;j<k;j++) if(a[i+j]<loc) loc=a[i+j];
        res=loc;
    }
    return res;
}
int window_max(int *a, int n, int k) {
    int res=a[0];
    for(int i=0;i<=n-k;i++){
        int loc=a[i];
        for(int j=1;j<k;j++) if(a[i+j]>loc) loc=a[i+j];
        if(i==0||loc>res) res=loc;
    }
    return res;
}
int window_range(int *a, int n, int k) { return window_max(a,n,k)-window_min(a,n,k); }
int main(void) {
    int a[]={3,1,4,1,5,9,2,6};
    printf("min=%d max=%d range=%d\n", window_min(a,8,3), window_max(a,8,3), window_range(a,8,3));
    return 0;
}
"""
PROJECTS.append({"batch":"03","name":"06_sliding_window","files":{"window.c":(
    _sw,
    _sw.replace("        res=loc;\n","        if(i==0||loc<res) res=loc;\n")
)},"truth":{"all_functions":["main","window_max","window_min","window_range"],
           "changed_functions":["window_min"],"affected_functions":["main","window_range"]}})

# 03/07 — strbuf: off-by-one in capacity check
_sb = r"""#include <stdio.h>
#include <string.h>
#define SB_CAP 128
typedef struct { char d[SB_CAP]; int len; } StrBuf;
void sb_init(StrBuf *s) { s->len=0; s->d[0]='\0'; }
int sb_append(StrBuf *s, const char *str) {
    int n=strlen(str);
    if(s->len+n > SB_CAP) return -1;
    memcpy(s->d+s->len, str, n);
    s->len+=n; s->d[s->len]='\0';
    return n;
}
int sb_len(StrBuf *s) { return s->len; }
void sb_clear(StrBuf *s) { s->len=0; s->d[0]='\0'; }
const char *sb_str(StrBuf *s) { return s->d; }
int main(void) {
    StrBuf sb; sb_init(&sb);
    sb_append(&sb,"hello"); sb_append(&sb," world");
    printf("[%s] len=%d\n", sb_str(&sb), sb_len(&sb));
    return 0;
}
"""
PROJECTS.append({"batch":"03","name":"07_strbuf","files":{"strbuf.c":(
    _sb,
    _sb.replace("if(s->len+n > SB_CAP)","if(s->len+n >= SB_CAP)")
)},"truth":{"all_functions":["main","sb_append","sb_clear","sb_init","sb_len","sb_str"],
           "changed_functions":["sb_append"],"affected_functions":["main"]}})

# 03/08 — median: partition comparison wrong
_md_before = r"""#include <stdio.h>
static void swap2(int *a,int *b){int t=*a;*a=*b;*b=t;}
static int partition2(int *a,int lo,int hi){
    int piv=a[hi],i=lo;
    for(int j=lo;j<hi;j++) if(a[j]<piv){swap2(&a[i],&a[j]);i++;}
    swap2(&a[i],&a[hi]); return i;
}
static int qsel(int *a,int lo,int hi,int k){
    if(lo>=hi) return a[lo];
    int p=partition2(a,lo,hi);
    if(p==k) return a[p];
    if(k<p) return qsel(a,lo,p-1,k);
    return qsel(a,p+1,hi,k);
}
int median(int *a, int n) { return qsel(a,0,n-1,n/2); }
int main(void) {
    int a[]={3,1,4,1,5};
    printf("median=%d\n", median(a,5));
    return 0;
}
"""
_md_after = _md_before.replace(
    "    for(int j=lo;j<hi;j++) if(a[j]<piv){swap2(&a[i],&a[j]);i++;}",
    "    for(int j=lo;j<hi;j++) if(a[j]<=piv){swap2(&a[i],&a[j]);i++;}")
PROJECTS.append({"batch":"03","name":"08_median","files":{"median.c":(_md_before,_md_after)},
"truth":{"all_functions":["main","median","partition2","qsel","swap2"],
         "changed_functions":["partition2"],"affected_functions":["main","median","qsel"]}})

# 03/09 — scheduler: sched_next tie-breaking wrong (>= vs >)
_sc = r"""#include <stdio.h>
#define SMAX 8
typedef struct { int id; int prio; int ready; } Task;
typedef struct { Task t[SMAX]; int n; } Sched;
void sched_init(Sched *s) { s->n=0; }
int sched_add(Sched *s, int id, int prio) {
    if(s->n>=SMAX) return -1;
    s->t[s->n].id=id; s->t[s->n].prio=prio; s->t[s->n].ready=1; s->n++;
    return 0;
}
int sched_next(Sched *s) {
    int best=-1;
    for(int i=0;i<s->n;i++){
        if(!s->t[i].ready) continue;
        if(best<0 || s->t[i].prio>=s->t[best].prio) best=i;
    }
    if(best>=0) s->t[best].ready=0;
    return best>=0 ? s->t[best].id : -1;
}
void sched_done(Sched *s, int id) {
    for(int i=0;i<s->n;i++) if(s->t[i].id==id){s->t[i].ready=1;break;}
}
int main(void) {
    Sched s; sched_init(&s);
    sched_add(&s,1,5); sched_add(&s,2,10); sched_add(&s,3,3);
    printf("next=%d\n", sched_next(&s));
    return 0;
}
"""
PROJECTS.append({"batch":"03","name":"09_scheduler","files":{"scheduler.c":(
    _sc,
    _sc.replace("s->t[i].prio>=s->t[best].prio","s->t[i].prio>s->t[best].prio")
)},"truth":{"all_functions":["main","sched_add","sched_done","sched_init","sched_next"],
           "changed_functions":["sched_next"],"affected_functions":["main"]}})

# 03/10 — debounce: >= vs > in delay check
_db = r"""#include <stdio.h>
typedef struct { int state; unsigned int last_time; unsigned int delay; } Debounce;
void db_init(Debounce *d, unsigned int delay) { d->state=0; d->last_time=0; d->delay=delay; }
int db_update(Debounce *d, int state, unsigned int now) {
    if(state != d->state){
        if(now - d->last_time > d->delay){
            d->state=state; d->last_time=now; return 1;
        }
    }
    return 0;
}
int db_state(Debounce *d) { return d->state; }
int main(void) {
    Debounce d; db_init(&d, 50);
    printf("%d %d\n", db_update(&d,1,100), db_state(&d));
    return 0;
}
"""
PROJECTS.append({"batch":"03","name":"10_debounce","files":{"debounce.c":(
    _db,
    _db.replace("now - d->last_time > d->delay","now - d->last_time >= d->delay")
)},"truth":{"all_functions":["db_init","db_state","db_update","main"],
           "changed_functions":["db_update"],"affected_functions":["main"]}})

# ═══════════════════════════════════════════════════════════════════════════
# BATCH 04
# ═══════════════════════════════════════════════════════════════════════════

# 04/01 — base64: first output char missing mask
_b64 = r"""#include <stdio.h>
static const char B64[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
int b64_encode(const unsigned char *in, int n, char *out, int sz) {
    int i=0,j=0;
    while(i<n){
        unsigned a=in[i++];
        unsigned b=i<n?in[i++]:0;
        unsigned c=i<n?in[i++]:0;
        out[j++]=B64[a>>2];
        out[j++]=B64[((a&3)<<4)|(b>>4)];
        out[j++]=B64[((b&0xF)<<2)|(c>>6)];
        out[j++]=B64[c&0x3F];
        if(j+4>sz) return -1;
    }
    out[j]='\0'; return j;
}
int b64_len(int n) { return ((n+2)/3)*4; }
int main(void) {
    unsigned char in[]="Man";
    char out[16];
    printf("n=%d s=%s\n", b64_encode(in,3,out,sizeof(out)), out);
    return 0;
}
"""
_b64_fixed = r"""#include <stdio.h>
static const char B64[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
int b64_encode(const unsigned char *in, int n, char *out, int sz) {
    int i=0,j=0;
    while(i<n){
        unsigned a=in[i++];
        unsigned b=i<n?in[i++]:0;
        unsigned c=i<n?in[i++]:0;
        int rem=n-(i-3);
        out[j++]=B64[(a>>2)&0x3F];
        out[j++]=B64[((a&3)<<4)|(b>>4)];
        out[j++]=rem>=2 ? B64[((b&0xF)<<2)|(c>>6)] : '=';
        out[j++]=rem>=3 ? B64[c&0x3F] : '=';
        if(j+4>sz) return -1;
    }
    out[j]='\0'; return j;
}
int b64_len(int n) { return ((n+2)/3)*4; }
int main(void) {
    unsigned char in[]="Man";
    char out[16];
    printf("n=%d s=%s\n", b64_encode(in,3,out,sizeof(out)), out);
    return 0;
}
"""
PROJECTS.append({"batch":"04","name":"01_base64","files":{"base64.c":(_b64,_b64_fixed)},
"truth":{"all_functions":["b64_encode","b64_len","main"],
         "changed_functions":["b64_encode"],"affected_functions":["main"]}})

# 04/02 — utf8: strlen advances by 1 instead of char width
_u8 = r"""#include <stdio.h>
int utf8_charlen(unsigned char c) {
    if(c<0x80) return 1;
    if((c&0xE0)==0xC0) return 2;
    if((c&0xF0)==0xE0) return 3;
    if((c&0xF8)==0xF0) return 4;
    return -1;
}
int utf8_strlen(const char *s) {
    int count=0;
    while(*s){
        int len=utf8_charlen((unsigned char)*s);
        if(len<0) return -1;
        s++;
        count++;
    }
    return count;
}
int utf8_valid(const char *s) {
    while(*s){ if(utf8_charlen((unsigned char)*s)<0) return 0; s++; }
    return 1;
}
int main(void) {
    printf("len=%d valid=%d\n", utf8_strlen("hello"), utf8_valid("hello"));
    return 0;
}
"""
PROJECTS.append({"batch":"04","name":"02_utf8","files":{"utf8.c":(
    _u8,
    _u8.replace("        s++;","        s+=len;")
)},"truth":{"all_functions":["main","utf8_charlen","utf8_strlen","utf8_valid"],
           "changed_functions":["utf8_strlen"],"affected_functions":["main"]}})

# 04/03 — varint: continuation bit always set
_vi = r"""#include <stdio.h>
int varint_encode(unsigned int v, unsigned char *out, int sz) {
    int i=0;
    do {
        if(i>=sz) return -1;
        out[i] = (v&0x7F)|0x80;
        v>>=7; i++;
    } while(v);
    return i;
}
int varint_decode(const unsigned char *in, int sz, unsigned int *out) {
    unsigned int v=0; int sh=0,i=0;
    do { if(i>=sz) return -1; v|=(unsigned int)(in[i]&0x7F)<<sh; sh+=7; i++; } while(in[i-1]&0x80);
    *out=v; return i;
}
int varint_size(unsigned int v) { int n=1; while(v>=128){v>>=7;n++;} return n; }
int main(void) {
    unsigned char buf[8];
    int n=varint_encode(300,buf,sizeof(buf));
    unsigned int v; varint_decode(buf,n,&v);
    printf("bytes=%d val=%u\n",n,v);
    return 0;
}
"""
PROJECTS.append({"batch":"04","name":"03_varint","files":{"varint.c":(
    _vi,
    _vi.replace(
        "        out[i] = (v&0x7F)|0x80;",
        "        out[i] = v&0x7F;\n        if(v>>7) out[i]|=0x80;")
)},"truth":{"all_functions":["main","varint_decode","varint_encode","varint_size"],
           "changed_functions":["varint_encode"],"affected_functions":["main"]}})

# 04/04 — bloom: bf_check uses OR instead of AND
_bf = r"""#include <stdio.h>
#include <string.h>
#define BF_BITS 256
typedef struct { unsigned char bits[BF_BITS/8]; } Bloom;
static unsigned bfh1(const char *s){unsigned h=5381;while(*s)h=h*33^(unsigned char)*s++;return h%BF_BITS;}
static unsigned bfh2(const char *s){unsigned h=0;while(*s)h=h*31+(unsigned char)*s++;return h%BF_BITS;}
void bf_init(Bloom *b) { memset(b->bits,0,sizeof(b->bits)); }
void bf_add(Bloom *b, const char *s) {
    unsigned h1=bfh1(s),h2=bfh2(s);
    b->bits[h1/8]|=1<<(h1%8); b->bits[h2/8]|=1<<(h2%8);
}
int bf_check(Bloom *b, const char *s) {
    unsigned h1=bfh1(s),h2=bfh2(s);
    return (b->bits[h1/8]>>(h1%8)&1) | (b->bits[h2/8]>>(h2%8)&1);
}
int main(void) {
    Bloom b; bf_init(&b); bf_add(&b,"hello");
    printf("hello=%d world=%d\n", bf_check(&b,"hello"), bf_check(&b,"world"));
    return 0;
}
"""
PROJECTS.append({"batch":"04","name":"04_bloom","files":{"bloom.c":(
    _bf,
    _bf.replace(
        "    return (b->bits[h1/8]>>(h1%8)&1) | (b->bits[h2/8]>>(h2%8)&1);",
        "    return (b->bits[h1/8]>>(h1%8)&1) && (b->bits[h2/8]>>(h2%8)&1);")
)},"truth":{"all_functions":["bf_add","bf_check","bf_init","bfh1","bfh2","main"],
           "changed_functions":["bf_check"],"affected_functions":["main"]}})

# 04/05 — trie: new node not initialized
_tr_before = r"""#include <stdio.h>
#include <string.h>
#define ALPHA 26
#define TNODES 128
typedef struct { int ch[ALPHA]; int end; } TNode;
typedef struct { TNode nodes[TNODES]; int n; } Trie;
void trie_init(Trie *t) {
    memset(t->nodes[0].ch,-1,sizeof(t->nodes[0].ch));
    t->nodes[0].end=0; t->n=1;
}
int trie_insert(Trie *t, const char *s) {
    int cur=0;
    while(*s){
        int c=*s-'a';
        if(t->nodes[cur].ch[c]<0){
            if(t->n>=TNODES) return -1;
            t->nodes[cur].ch[c]=t->n++;
        }
        cur=t->nodes[cur].ch[c]; s++;
    }
    t->nodes[cur].end=1; return 0;
}
int trie_search(Trie *t, const char *s) {
    int cur=0;
    while(*s){ int c=*s-'a'; if(t->nodes[cur].ch[c]<0) return 0; cur=t->nodes[cur].ch[c]; s++; }
    return t->nodes[cur].end;
}
int main(void) {
    Trie t; trie_init(&t);
    trie_insert(&t,"hello");
    printf("hello=%d world=%d\n", trie_search(&t,"hello"), trie_search(&t,"world"));
    return 0;
}
"""
_tr_after = _tr_before.replace(
    "            if(t->n>=TNODES) return -1;\n            t->nodes[cur].ch[c]=t->n++;",
    "            if(t->n>=TNODES) return -1;\n            memset(t->nodes[t->n].ch,-1,sizeof(t->nodes[t->n].ch));\n            t->nodes[t->n].end=0;\n            t->nodes[cur].ch[c]=t->n++;")
PROJECTS.append({"batch":"04","name":"05_trie","files":{"trie.c":(_tr_before,_tr_after)},
"truth":{"all_functions":["main","trie_init","trie_insert","trie_search"],
         "changed_functions":["trie_insert"],"affected_functions":["main","trie_search"]}})

# 04/06 — dfa: set_trans missing bounds check
_dfa = r"""#include <stdio.h>
#define ST 4
#define AL 2
typedef struct { int tr[ST][AL]; int acc[ST]; int start; } DFA;
void dfa_init(DFA *d, int s) {
    d->start=s;
    for(int i=0;i<ST;i++){d->acc[i]=0;for(int j=0;j<AL;j++)d->tr[i][j]=-1;}
}
void dfa_set(DFA *d, int from, int sym, int to) {
    d->tr[from][sym]=to;
}
int dfa_run(DFA *d, const int *inp, int n) {
    int st=d->start;
    for(int i=0;i<n;i++){ if(st<0)return 0; st=d->tr[st][inp[i]]; }
    return st>=0&&d->acc[st];
}
int dfa_accepts(DFA *d, const int *inp, int n) { return dfa_run(d,inp,n); }
int main(void) {
    DFA d; dfa_init(&d,0);
    dfa_set(&d,0,0,1); dfa_set(&d,1,1,2); d.acc[2]=1;
    int inp[]={0,1};
    printf("accepted=%d\n", dfa_accepts(&d,inp,2));
    return 0;
}
"""
PROJECTS.append({"batch":"04","name":"06_dfa","files":{"dfa.c":(
    _dfa,
    _dfa.replace(
        "void dfa_set(DFA *d, int from, int sym, int to) {\n    d->tr[from][sym]=to;\n}",
        "void dfa_set(DFA *d, int from, int sym, int to) {\n    if(from<0||from>=ST||sym<0||sym>=AL) return;\n    d->tr[from][sym]=to;\n}")
)},"truth":{"all_functions":["dfa_accepts","dfa_init","dfa_run","dfa_set","main"],
           "changed_functions":["dfa_set"],"affected_functions":["main"]}})

# 04/07 — json_writer: string not escaped
_jw = r"""#include <stdio.h>
#include <string.h>
#define JWCAP 256
typedef struct { char buf[JWCAP]; int pos; } JW;
void jw_init(JW *w) { w->pos=0; w->buf[0]='\0'; }
static int jw_raw(JW *w, const char *s) {
    int n=strlen(s);
    if(w->pos+n>=JWCAP) return -1;
    memcpy(w->buf+w->pos,s,n); w->pos+=n; w->buf[w->pos]='\0';
    return n;
}
int jw_string(JW *w, const char *s) {
    jw_raw(w,"\"");
    while(*s){ char c[2]={*s,0}; jw_raw(w,c); s++; }
    return jw_raw(w,"\"");
}
int jw_int(JW *w, int v) { char t[32]; sprintf(t,"%d",v); return jw_raw(w,t); }
const char *jw_get(JW *w) { return w->buf; }
int main(void) {
    JW w; jw_init(&w);
    jw_raw(&w,"{\"k\":"); jw_string(&w,"hel\"lo"); jw_raw(&w,"}");
    printf("%s\n", jw_get(&w));
    return 0;
}
"""
_jw_fixed = _jw.replace(
    '    while(*s){ char c[2]={*s,0}; jw_raw(w,c); s++; }',
    '    while(*s){\n        if(*s==\'"\') jw_raw(w,"\\\\\"");\n        else if(*s==\'\\\\\') jw_raw(w,"\\\\\\\\");\n        else { char c[2]={*s,0}; jw_raw(w,c); }\n        s++;\n    }')
PROJECTS.append({"batch":"04","name":"07_json_writer","files":{"jsonw.c":(_jw,_jw_fixed)},
"truth":{"all_functions":["jw_get","jw_init","jw_int","jw_raw","jw_string","main"],
         "changed_functions":["jw_string"],"affected_functions":["main"]}})

# 04/08 — csv: quoted field not handled
_csv_before = r"""#include <stdio.h>
#include <string.h>
typedef struct { const char *src; int pos; } CSV;
void csv_init(CSV *c, const char *src) { c->src=src; c->pos=0; }
int csv_next(CSV *c, char *out, int sz) {
    if(!c->src[c->pos]) return 0;
    int j=0;
    while(c->src[c->pos]&&c->src[c->pos]!=','){
        if(j<sz-1) out[j++]=c->src[c->pos];
        c->pos++;
    }
    if(c->src[c->pos]==',') c->pos++;
    out[j]='\0'; return 1;
}
int csv_count(const char *line) {
    CSV c; csv_init(&c,line);
    char buf[256]; int n=0;
    while(csv_next(&c,buf,sizeof(buf))) n++;
    return n;
}
int main(void) {
    CSV c; csv_init(&c,"a,\"b,c\",d");
    char f[64];
    while(csv_next(&c,f,sizeof(f))) printf("[%s]\n",f);
    return 0;
}
"""
_csv_after = r"""#include <stdio.h>
#include <string.h>
typedef struct { const char *src; int pos; } CSV;
void csv_init(CSV *c, const char *src) { c->src=src; c->pos=0; }
int csv_next(CSV *c, char *out, int sz) {
    if(!c->src[c->pos]) return 0;
    int j=0;
    if(c->src[c->pos]=='"'){
        c->pos++;
        while(c->src[c->pos]&&c->src[c->pos]!='"'){
            if(j<sz-1) out[j++]=c->src[c->pos];
            c->pos++;
        }
        if(c->src[c->pos]=='"') c->pos++;
    } else {
        while(c->src[c->pos]&&c->src[c->pos]!=','){
            if(j<sz-1) out[j++]=c->src[c->pos];
            c->pos++;
        }
    }
    if(c->src[c->pos]==',') c->pos++;
    out[j]='\0'; return 1;
}
int csv_count(const char *line) {
    CSV c; csv_init(&c,line);
    char buf[256]; int n=0;
    while(csv_next(&c,buf,sizeof(buf))) n++;
    return n;
}
int main(void) {
    CSV c; csv_init(&c,"a,\"b,c\",d");
    char f[64];
    while(csv_next(&c,f,sizeof(f))) printf("[%s]\n",f);
    return 0;
}
"""
PROJECTS.append({"batch":"04","name":"08_csv","files":{"csv.c":(_csv_before,_csv_after)},
"truth":{"all_functions":["csv_count","csv_init","csv_next","main"],
         "changed_functions":["csv_next"],"affected_functions":["csv_count","main"]}})

# 04/09 — argparse: -- prefix not stripped
_ap = r"""#include <stdio.h>
#include <string.h>
#define APMAX 8
typedef struct { const char *name; int found; } Arg;
typedef struct { Arg args[APMAX]; int n; } AP;
void ap_init(AP *p) { p->n=0; }
int ap_add(AP *p, const char *name) {
    if(p->n>=APMAX) return -1;
    p->args[p->n].name=name; p->args[p->n].found=0; p->n++;
    return 0;
}
int ap_parse(AP *p, int argc, char **argv) {
    for(int i=1;i<argc;i++){
        if(argv[i][0]!='-') continue;
        const char *flag=argv[i]+1;
        for(int j=0;j<p->n;j++)
            if(strcmp(p->args[j].name,flag)==0) p->args[j].found=1;
    }
    return 0;
}
int ap_found(AP *p, const char *name) {
    for(int i=0;i<p->n;i++) if(strcmp(p->args[i].name,name)==0) return p->args[i].found;
    return 0;
}
int main(void) {
    AP p; ap_init(&p); ap_add(&p,"verbose");
    char *args[]={"prog","--verbose"};
    ap_parse(&p,2,args);
    printf("verbose=%d\n", ap_found(&p,"verbose"));
    return 0;
}
"""
PROJECTS.append({"batch":"04","name":"09_argparse","files":{"argparse.c":(
    _ap,
    _ap.replace(
        "        const char *flag=argv[i]+1;",
        "        const char *flag=argv[i]+1;\n        if(flag[0]=='-') flag++;")
)},"truth":{"all_functions":["ap_add","ap_found","ap_init","ap_parse","main"],
           "changed_functions":["ap_parse"],"affected_functions":["main"]}})

# 04/10 — env: value not trimmed
_env = r"""#include <stdio.h>
#include <string.h>
#define EMAX 16
typedef struct { char k[64]; char v[128]; } EEntry;
typedef struct { EEntry e[EMAX]; int n; } Env;
void env_init(Env *s) { s->n=0; }
static void trim_end(char *s) {
    int i=strlen(s)-1;
    while(i>=0&&(s[i]==' '||s[i]=='\t'||s[i]=='\r'||s[i]=='\n')) s[i--]='\0';
}
int env_load(Env *s, const char *line) {
    if(s->n>=EMAX) return -1;
    const char *eq=strchr(line,'=');
    if(!eq) return -1;
    int kl=eq-line; if(kl>=64) return -1;
    strncpy(s->e[s->n].k,line,kl); s->e[s->n].k[kl]='\0';
    strncpy(s->e[s->n].v,eq+1,127);
    s->n++; return 0;
}
const char *env_get(Env *s, const char *k, const char *def) {
    for(int i=0;i<s->n;i++) if(strcmp(s->e[i].k,k)==0) return s->e[i].v;
    return def;
}
int main(void) {
    Env s; env_init(&s);
    env_load(&s,"HOST=localhost  ");
    printf("HOST=[%s]\n", env_get(&s,"HOST","none"));
    return 0;
}
"""
PROJECTS.append({"batch":"04","name":"10_env","files":{"env.c":(
    _env,
    _env.replace(
        "    strncpy(s->e[s->n].v,eq+1,127);\n    s->n++; return 0;",
        "    strncpy(s->e[s->n].v,eq+1,127);\n    trim_end(s->e[s->n].v);\n    s->n++; return 0;")
)},"truth":{"all_functions":["env_get","env_init","env_load","main","trim_end"],
           "changed_functions":["env_load"],"affected_functions":["main"]}})

# ═══════════════════════════════════════════════════════════════════════════
# BATCH 05
# ═══════════════════════════════════════════════════════════════════════════

# 05/01 — retry: wrong backoff formula
_rt = r"""#include <stdio.h>
typedef int (*Fn)(void*);
int retry_run(Fn fn, void *ctx, int max, unsigned int delay) {
    for(int i=0;i<max;i++){
        if(fn(ctx)==0) return 0;
        if(i<max-1){ unsigned int w=delay*i; (void)w; }
    }
    return -1;
}
int retry_count(Fn fn, void *ctx, int max) {
    int n=0;
    for(int i=0;i<max;i++){ n++; if(fn(ctx)==0) break; }
    return n;
}
static int always_fail(void *c){(void)c;return -1;}
static int always_ok(void *c){(void)c;return 0;}
int main(void) {
    printf("fail=%d ok=%d\n", retry_run(always_fail,0,3,10), retry_run(always_ok,0,3,10));
    return 0;
}
"""
PROJECTS.append({"batch":"05","name":"01_retry","files":{"retry.c":(
    _rt,
    _rt.replace("unsigned int w=delay*i;","unsigned int w=delay<<i;")
)},"truth":{"all_functions":["always_fail","always_ok","main","retry_count","retry_run"],
           "changed_functions":["retry_run"],"affected_functions":["main"]}})

# 05/02 — circuit_breaker: HALF state not allowed
_cb = r"""#include <stdio.h>
#define CB_CLOSED 0
#define CB_OPEN   1
#define CB_HALF   2
typedef struct { int state; int fails; int threshold; } CB;
void cb_init(CB *c, int thr) { c->state=CB_CLOSED; c->fails=0; c->threshold=thr; }
int cb_allow(CB *c) { return c->state==CB_CLOSED; }
void cb_success(CB *c) {
    c->fails=0;
    if(c->state==CB_HALF) c->state=CB_CLOSED;
}
void cb_failure(CB *c) {
    c->fails++;
    if(c->fails>=c->threshold) c->state=CB_OPEN;
}
int cb_state(CB *c) { return c->state; }
int main(void) {
    CB c; cb_init(&c,3);
    cb_failure(&c); cb_failure(&c); cb_failure(&c);
    printf("allow=%d state=%d\n", cb_allow(&c), cb_state(&c));
    return 0;
}
"""
PROJECTS.append({"batch":"05","name":"02_circuit_breaker","files":{"circuit.c":(
    _cb,
    _cb.replace("int cb_allow(CB *c) { return c->state==CB_CLOSED; }",
                "int cb_allow(CB *c) { return c->state!=CB_OPEN; }")
)},"truth":{"all_functions":["cb_allow","cb_failure","cb_init","cb_state","cb_success","main"],
           "changed_functions":["cb_allow"],"affected_functions":["main"]}})

# 05/03 — leaky_bucket: drain never reduces level
_lb = r"""#include <stdio.h>
#define LBCAP 100
typedef struct { int level; int rate; unsigned int last; } LB;
void lb_init(LB *b, int rate) { b->level=0; b->rate=rate; b->last=0; }
static void lb_drain(LB *b, unsigned int now) {
    unsigned int elapsed=now-b->last;
    b->last=now;
    if(b->level<0) b->level=0;
}
int lb_add(LB *b, int amount, unsigned int now) {
    lb_drain(b,now);
    if(b->level+amount>LBCAP) return -1;
    b->level+=amount; return 0;
}
int lb_level(LB *b) { return b->level; }
int main(void) {
    LB b; lb_init(&b,10);
    lb_add(&b,50,0); lb_add(&b,30,3);
    printf("level=%d\n", lb_level(&b));
    return 0;
}
"""
PROJECTS.append({"batch":"05","name":"03_leaky_bucket","files":{"leaky.c":(
    _lb,
    _lb.replace(
        "    unsigned int elapsed=now-b->last;\n    b->last=now;\n    if(b->level<0) b->level=0;",
        "    unsigned int elapsed=now-b->last;\n    int drain=(int)elapsed*b->rate;\n    b->level-=drain;\n    b->last=now;\n    if(b->level<0) b->level=0;")
)},"truth":{"all_functions":["lb_add","lb_drain","lb_init","lb_level","main"],
           "changed_functions":["lb_drain"],"affected_functions":["lb_add","main"]}})

# 05/04 — conn_pool: acquired_at not recorded
_cp = r"""#include <stdio.h>
#define CPMAX 4
typedef struct { int id; int in_use; unsigned int acquired_at; } Conn;
typedef struct { Conn c[CPMAX]; unsigned int timeout; } Pool;
void cp_init(Pool *p, unsigned int timeout) {
    p->timeout=timeout;
    for(int i=0;i<CPMAX;i++){p->c[i].id=i;p->c[i].in_use=0;}
}
int cp_acquire(Pool *p, unsigned int now) {
    for(int i=0;i<CPMAX;i++){
        if(!p->c[i].in_use){p->c[i].in_use=1; return i;}
    }
    return -1;
}
void cp_release(Pool *p, int id) { if(id>=0&&id<CPMAX) p->c[id].in_use=0; }
int cp_expire(Pool *p, unsigned int now) {
    int count=0;
    for(int i=0;i<CPMAX;i++)
        if(p->c[i].in_use&&now-p->c[i].acquired_at>p->timeout){p->c[i].in_use=0;count++;}
    return count;
}
int main(void) {
    Pool p; cp_init(&p,30);
    int c=cp_acquire(&p,0);
    printf("conn=%d expired=%d\n",c,cp_expire(&p,100));
    cp_release(&p,c);
    return 0;
}
"""
PROJECTS.append({"batch":"05","name":"04_conn_pool","files":{"connpool.c":(
    _cp,
    _cp.replace(
        "        if(!p->c[i].in_use){p->c[i].in_use=1; return i;}",
        "        if(!p->c[i].in_use){p->c[i].in_use=1; p->c[i].acquired_at=now; return i;}")
)},"truth":{"all_functions":["cp_acquire","cp_expire","cp_init","cp_release","main"],
           "changed_functions":["cp_acquire"],"affected_functions":["main"]}})

# 05/05 — event_bus: emit only calls first handler
_eb_before = r"""#include <stdio.h>
#define EBMAX 4
#define EHMAX 4
typedef void (*Hfn)(int,void*);
typedef struct { int ev; Hfn h[EHMAX]; int n; } ESlot;
typedef struct { ESlot s[EBMAX]; int n; } EB;
void eb_init(EB *b) { b->n=0; }
int eb_sub(EB *b, int ev, Hfn h) {
    for(int i=0;i<b->n;i++)
        if(b->s[i].ev==ev){if(b->s[i].n>=EHMAX)return -1;b->s[i].h[b->s[i].n++]=h;return 0;}
    if(b->n>=EBMAX) return -1;
    b->s[b->n].ev=ev; b->s[b->n].h[0]=h; b->s[b->n].n=1; b->n++;
    return 0;
}
int eb_emit(EB *b, int ev, void *data) {
    for(int i=0;i<b->n;i++)
        if(b->s[i].ev==ev){ b->s[i].h[0](ev,data); return 1; }
    return 0;
}
int eb_count(EB *b, int ev) {
    for(int i=0;i<b->n;i++) if(b->s[i].ev==ev) return b->s[i].n;
    return 0;
}
static void on_ev(int e,void*d){(void)d;printf("event=%d\n",e);}
int main(void) {
    EB b; eb_init(&b); eb_sub(&b,1,on_ev);
    printf("cnt=%d emit=%d\n", eb_count(&b,1), eb_emit(&b,1,0));
    return 0;
}
"""
_eb_after = _eb_before.replace(
    "        if(b->s[i].ev==ev){ b->s[i].h[0](ev,data); return 1; }",
    "        if(b->s[i].ev==ev){ for(int j=0;j<b->s[i].n;j++) b->s[i].h[j](ev,data); return b->s[i].n; }")
PROJECTS.append({"batch":"05","name":"05_event_bus","files":{"eventbus.c":(_eb_before,_eb_after)},
"truth":{"all_functions":["eb_count","eb_emit","eb_init","eb_sub","main","on_ev"],
         "changed_functions":["eb_emit"],"affected_functions":["main"]}})

# 05/06 — ini_parser: section null-term missing
_ini = r"""#include <stdio.h>
#include <string.h>
#define IMAX 16
typedef struct { char sec[32]; char k[64]; char v[128]; } IniE;
typedef struct { IniE e[IMAX]; int n; } Ini;
void ini_init(Ini *s) { s->n=0; }
int ini_load(Ini *s, const char *line, char *cur_sec) {
    if(line[0]=='['){
        int end=strcspn(line+1,"]");
        strncpy(cur_sec,line+1,end);
        return 0;
    }
    const char *eq=strchr(line,'=');
    if(!eq||s->n>=IMAX) return -1;
    IniE *e=&s->e[s->n++];
    strncpy(e->sec,cur_sec,31);
    int kl=eq-line; if(kl>=64)kl=63;
    strncpy(e->k,line,kl); e->k[kl]='\0';
    strncpy(e->v,eq+1,127);
    return 1;
}
const char *ini_get(Ini *s,const char *sec,const char *k,const char *def){
    for(int i=0;i<s->n;i++)
        if(strcmp(s->e[i].sec,sec)==0&&strcmp(s->e[i].k,k)==0) return s->e[i].v;
    return def;
}
int main(void) {
    Ini s; ini_init(&s); char sec[32]="";
    ini_load(&s,"[db]",sec); ini_load(&s,"host=localhost",sec);
    printf("host=[%s]\n", ini_get(&s,"db","host","none"));
    return 0;
}
"""
PROJECTS.append({"batch":"05","name":"06_ini_parser","files":{"ini.c":(
    _ini,
    _ini.replace(
        "        strncpy(cur_sec,line+1,end);\n        return 0;",
        "        strncpy(cur_sec,line+1,end);\n        cur_sec[end]='\\0';\n        return 0;")
)},"truth":{"all_functions":["ini_get","ini_init","ini_load","main"],
           "changed_functions":["ini_load"],"affected_functions":["main"]}})

# 05/07 — log_rotate: no validation for bytes <= 0
_lr = r"""#include <stdio.h>
#define MAXSZ 1000
typedef struct { int size; int max; int rotations; } LR;
void lr_init(LR *l, int max) { l->size=0; l->max=max; l->rotations=0; }
int lr_write(LR *l, int bytes) {
    if(l->size+bytes>l->max){ l->rotations++; l->size=0; }
    l->size+=bytes; return 0;
}
int lr_rotations(LR *l) { return l->rotations; }
int lr_remaining(LR *l) { return l->max-l->size; }
int lr_should_rotate(LR *l, int bytes) { return l->size+bytes>l->max; }
int main(void) {
    LR l; lr_init(&l,MAXSZ);
    lr_write(&l,600); lr_write(&l,600);
    printf("rotations=%d remaining=%d\n", lr_rotations(&l), lr_remaining(&l));
    return 0;
}
"""
PROJECTS.append({"batch":"05","name":"07_log_rotate","files":{"logrot.c":(
    _lr,
    _lr.replace(
        "int lr_write(LR *l, int bytes) {\n    if(l->size+bytes>l->max)",
        "int lr_write(LR *l, int bytes) {\n    if(bytes<=0) return -1;\n    if(l->size+bytes>l->max)")
)},"truth":{"all_functions":["lr_init","lr_remaining","lr_rotations","lr_should_rotate","lr_write","main"],
           "changed_functions":["lr_write"],"affected_functions":["main"]}})

# 05/08 — cache: always evicts slot 0 instead of LRU
_ca_before = r"""#include <stdio.h>
#include <string.h>
#define CSZ 4
typedef struct { int key; int val; int age; } CE;
typedef struct { CE e[CSZ]; int tick; } Cache;
void cache_init(Cache *c) { c->tick=0; memset(c->e,0,sizeof(c->e)); }
void cache_put(Cache *c, int k, int v) {
    for(int i=0;i<CSZ;i++)
        if(c->e[i].key==k){c->e[i].val=v;c->e[i].age=c->tick++;return;}
    c->e[0]=(CE){k,v,c->tick++};
}
int cache_get(Cache *c, int k, int *out) {
    for(int i=0;i<CSZ;i++)
        if(c->e[i].key==k){c->e[i].age=c->tick++;*out=c->e[i].val;return 1;}
    return 0;
}
int cache_stale(Cache *c, int max_age) {
    int n=0; for(int i=0;i<CSZ;i++) if(c->e[i].age<max_age) n++;
    return n;
}
int main(void) {
    Cache c; cache_init(&c);
    cache_put(&c,1,10); cache_put(&c,2,20);
    int v; cache_get(&c,1,&v);
    printf("v=%d stale=%d\n",v,cache_stale(&c,2));
    return 0;
}
"""
_ca_after = _ca_before.replace(
    "    c->e[0]=(CE){k,v,c->tick++};",
    "    int old=0;\n    for(int i=1;i<CSZ;i++) if(c->e[i].age<c->e[old].age) old=i;\n    c->e[old]=(CE){k,v,c->tick++};")
PROJECTS.append({"batch":"05","name":"08_cache","files":{"cache.c":(_ca_before,_ca_after)},
"truth":{"all_functions":["cache_get","cache_init","cache_put","cache_stale","main"],
         "changed_functions":["cache_put"],"affected_functions":["main"]}})

# 05/09 — pubsub: publish only notifies first subscriber
_ps_before = r"""#include <stdio.h>
#define PSMAX 4
#define SHMAX 4
typedef void (*SubFn)(const char*,const char*);
typedef struct { const char *topic; SubFn h[SHMAX]; int n; } PSSlot;
typedef struct { PSSlot s[PSMAX]; int n; } PS;
void ps_init(PS *p) { p->n=0; }
int ps_sub(PS *p, const char *t, SubFn fn) {
    for(int i=0;i<p->n;i++)
        if(p->s[i].topic==t){if(p->s[i].n>=SHMAX)return -1;p->s[i].h[p->s[i].n++]=fn;return 0;}
    if(p->n>=PSMAX) return -1;
    p->s[p->n].topic=t; p->s[p->n].h[0]=fn; p->s[p->n].n=1; p->n++;
    return 0;
}
int ps_pub(PS *p, const char *t, const char *msg) {
    for(int i=0;i<p->n;i++)
        if(p->s[i].topic==t){ p->s[i].h[0](t,msg); return 1; }
    return 0;
}
int ps_count(PS *p, const char *t) {
    for(int i=0;i<p->n;i++) if(p->s[i].topic==t) return p->s[i].n;
    return 0;
}
static const char *TA="a";
static void on_msg(const char *t,const char *m){printf("[%s] %s\n",t,m);}
int main(void) {
    PS p; ps_init(&p); ps_sub(&p,TA,on_msg);
    printf("delivered=%d subs=%d\n", ps_pub(&p,TA,"hi"), ps_count(&p,TA));
    return 0;
}
"""
_ps_after = _ps_before.replace(
    "        if(p->s[i].topic==t){ p->s[i].h[0](t,msg); return 1; }",
    "        if(p->s[i].topic==t){ for(int j=0;j<p->s[i].n;j++) p->s[i].h[j](t,msg); return p->s[i].n; }")
PROJECTS.append({"batch":"05","name":"09_pubsub","files":{"pubsub.c":(_ps_before,_ps_after)},
"truth":{"all_functions":["main","on_msg","ps_count","ps_init","ps_pub","ps_sub"],
         "changed_functions":["ps_pub"],"affected_functions":["main"]}})

# 05/10 — middleware: chain passes original request, not chained response
_mw = r"""#include <stdio.h>
#define MWMAX 8
typedef int (*MFn)(int,int*);
typedef struct { MFn chain[MWMAX]; int n; } MWC;
void mw_init(MWC *c) { c->n=0; }
int mw_use(MWC *c, MFn fn) { if(c->n>=MWMAX)return -1; c->chain[c->n++]=fn; return 0; }
int mw_run(MWC *c, int req, int *resp) {
    *resp=req;
    for(int i=0;i<c->n;i++){
        int r=c->chain[i](req,resp);
        if(r!=0) return r;
    }
    return 0;
}
int mw_count(MWC *c) { return c->n; }
static int dbl(int r,int *o){*o=r*2;return 0;}
static int inc(int r,int *o){*o=r+1;return 0;}
int main(void) {
    MWC c; mw_init(&c); mw_use(&c,dbl); mw_use(&c,inc);
    int resp; mw_run(&c,5,&resp);
    printf("result=%d count=%d\n", resp, mw_count(&c));
    return 0;
}
"""
PROJECTS.append({"batch":"05","name":"10_middleware","files":{"middleware.c":(
    _mw,
    _mw.replace(
        "        int r=c->chain[i](req,resp);",
        "        int r=c->chain[i](*resp,resp);")
)},"truth":{"all_functions":["dbl","inc","main","mw_count","mw_init","mw_run","mw_use"],
           "changed_functions":["mw_run"],"affected_functions":["main"]}})

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"Creating {len(PROJECTS)} projects across 4 batches...\n")
    for proj in PROJECTS:
        create(proj)
    print(f"\nDone. Run: python scripts/run_batch.py")

if __name__ == "__main__":
    main()
