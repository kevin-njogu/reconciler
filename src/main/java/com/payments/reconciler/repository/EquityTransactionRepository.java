package com.payments.reconciler.repository;

import com.payments.reconciler.entity.EquityTransaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Repository interface for managing EquityTransaction entities.
 * This interface extends JpaRepository, providing built-in CRUD operations
 * and query methods for interacting with the database.
 */
@Repository
public interface EquityTransactionRepository extends JpaRepository<EquityTransaction, Long> {
}
