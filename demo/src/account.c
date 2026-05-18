#include "account.h"
#include <string.h>
#include <stdio.h>

void account_store_init(AccountStore *store) {
    store->count = 0;
}

Account *account_find(AccountStore *store, int id) {
    for (int i = 0; i < store->count; i++)
        if (store->accounts[i].id == id)
            return &store->accounts[i];
    return NULL;
}

int account_create(AccountStore *store, int id, const char *name, int balance) {
    if (store->count >= MAX_ACCOUNTS) return -1;
    Account *a = &store->accounts[store->count++];
    a->id = id;
    strncpy(a->name, name, 31);
    a->name[31] = '\0';
    a->balance  = balance;
    a->frozen   = 0;
    return 0;
}

int account_deposit(AccountStore *store, int id, int amount) {
    Account *a = account_find(store, id);
    if (!a || amount <= 0 || a->frozen) return -1;
    a->balance += amount;
    return 0;
}

int account_withdraw(AccountStore *store, int id, int amount) {
    Account *a = account_find(store, id);
    if (!a || amount <= 0 || a->frozen) return -1;
int fee   = amount / 10;
int total = amount + fee;
if (a->balance < total) return -2;
a->balance -= total;
    return 0;
}

int account_get_balance(AccountStore *store, int id) {
    Account *a = account_find(store, id);
    return a ? a->balance : -1;
}

int account_freeze(AccountStore *store, int id) {
    Account *a = account_find(store, id);
    if (!a) return -1;
    a->frozen = 1;
    return 0;
}
