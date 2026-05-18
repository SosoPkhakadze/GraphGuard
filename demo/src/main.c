#include <stdio.h>
#include "account.h"
#include "transaction.h"
#include "report.h"

int main(void) {
    AccountStore store;
    TxLog        log;

    account_store_init(&store);
    tx_log_init(&log);

    /* create accounts */
    account_create(&store, 1, "Alice",  1100);
    account_create(&store, 2, "Bob",     500);
    account_create(&store, 3, "Carol",   200);
    account_create(&store, 4, "Dave",   3000);

    /* run transactions */
    tx_execute(&log, &store, TX_DEPOSIT,  0, 1,  300);   /* Alice  +300  */
    tx_execute(&log, &store, TX_WITHDRAW, 2, 0,  100);   /* Bob    -100  */
    tx_execute(&log, &store, TX_TRANSFER, 1, 2,  200);   /* Alice->Bob   */
    tx_execute(&log, &store, TX_WITHDRAW, 3, 0,  500);   /* Carol: FAIL  */
    tx_execute(&log, &store, TX_TRANSFER, 4, 3, 1500);   /* Dave->Carol  */
    tx_execute(&log, &store, TX_WITHDRAW, 4, 0, 9999);   /* Dave:  FAIL  */

    report_summary(&store, &log);
    return 0;
}
