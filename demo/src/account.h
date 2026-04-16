#ifndef ACCOUNT_H
#define ACCOUNT_H

#define MAX_ACCOUNTS 32

typedef struct {
    int  id;
    char name[32];
    int  balance;
    int  frozen;
} Account;

typedef struct {
    Account accounts[MAX_ACCOUNTS];
    int     count;
} AccountStore;

void     account_store_init  (AccountStore *store);
int      account_create      (AccountStore *store, int id, const char *name, int balance);
Account *account_find        (AccountStore *store, int id);
int      account_deposit     (AccountStore *store, int id, int amount);
int      account_withdraw    (AccountStore *store, int id, int amount);
int      account_get_balance (AccountStore *store, int id);
int      account_freeze      (AccountStore *store, int id);

#endif
