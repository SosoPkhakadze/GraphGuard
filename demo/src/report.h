#ifndef REPORT_H
#define REPORT_H
#include "account.h"
#include "transaction.h"

int  report_net_worth  (AccountStore *store);
void report_failed_txs (TxLog *log);
void report_balances   (AccountStore *store);
void report_summary    (AccountStore *store, TxLog *log);

#endif
