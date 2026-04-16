#include "report.h"
#include <stdio.h>

int report_net_worth(AccountStore *store) {
    int total = 0;
    for (int i = 0; i < store->count; i++)
        if (!store->accounts[i].frozen)
            total += store->accounts[i].balance;
    return total;
}

void report_failed_txs(TxLog *log) {
    int n = tx_count_failed(log);
    printf("  Failed transactions : %d / %d\n", n, log->count);
}

void report_balances(AccountStore *store) {
    printf("  Account balances:\n");
    for (int i = 0; i < store->count; i++) {
        Account *a = &store->accounts[i];
        printf("    [%d] %-12s  $%d%s\n",
               a->id, a->name, a->balance,
               a->frozen ? "  [FROZEN]" : "");
    }
}

void report_summary(AccountStore *store, TxLog *log) {
    printf("\n========== ACCOUNT SYSTEM REPORT ==========\n");
    printf("  Accounts       : %d\n",   store->count);
    printf("  Net worth      : $%d\n",  report_net_worth(store));
    printf("  Transactions   : %d\n",   log->count);
    printf("  Successful     : %d\n",   tx_count_ok(log));
    printf("  Failed         : %d\n",   tx_count_failed(log));
    printf("  Total volume   : $%d\n",  tx_total_volume(log));
    printf("===========================================\n");
    report_balances(store);
    report_failed_txs(log);
    printf("===========================================\n\n");
}
