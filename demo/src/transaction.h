#ifndef TRANSACTION_H
#define TRANSACTION_H
#include "account.h"

#define MAX_TX 64

typedef enum { TX_DEPOSIT, TX_WITHDRAW, TX_TRANSFER } TxType;

typedef struct {
    int    id;
    TxType type;
    int    from_id;
    int    to_id;
    int    amount;
    int    status;   /* 1 = ok, -1 = failed */
} Transaction;

typedef struct {
    Transaction txs[MAX_TX];
    int         count;
} TxLog;

void tx_log_init    (TxLog *log);
int  tx_execute     (TxLog *log, AccountStore *store,
                     TxType type, int from_id, int to_id, int amount);
int  tx_count_ok    (TxLog *log);
int  tx_count_failed(TxLog *log);
int  tx_total_volume(TxLog *log);

#endif
