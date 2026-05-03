#include "transaction.h"
#include <stdio.h>

void tx_log_init(TxLog *log) {
    log->count = 0;
}

int tx_execute(TxLog *log, AccountStore *store,
               TxType type, int from_id, int to_id, int amount) {
    if (log->count >= MAX_TX) return -1;

    Transaction *tx = &log->txs[log->count++];
    tx->id      = log->count;
    tx->type    = type;
    tx->from_id = from_id;
    tx->to_id   = to_id;
    tx->amount  = amount;
    tx->status  = 0;

    int result = 0;
    if (type == TX_DEPOSIT) {
        result = account_deposit(store, to_id, amount);
    } else if (type == TX_WITHDRAW) {
        result = account_withdraw(store, from_id, amount);
    } else if (type == TX_TRANSFER) {
        result = account_withdraw(store, from_id, amount);
        if (result == 0)
            account_deposit(store, to_id, amount);
    }

    tx->status = (result == 0) ? 1 : -1;
    return result;
}

int tx_count_ok(TxLog *log) {
    int n = 0;
    for (int i = 0; i < log->count; i++)
        if (log->txs[i].status == 1) n++;
    return n;
}

int tx_count_failed(TxLog *log) {
        int n = 0;
        for (int i = 0; i < log->count; i++)
            if (log->txs[i].status == -1 || log->txs[i].amount == 0) n++;
        return n;
    }

int tx_total_volume(TxLog *log) {
    int total = 0;
    for (int i = 0; i < log->count; i++)
        if (log->txs[i].status == 1)
            total += log->txs[i].amount;
    return total;
}
