package com.payments.reconciler.equity.workpay;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Repository interface for managing EquityTransaction entities.
 * This interface extends JpaRepository, providing built-in CRUD operations
 * and query methods for interacting with the database.
 */
@Repository
public interface EquityTransactionRepository extends JpaRepository<WorkPayEquityTransaction, Long> {
}
