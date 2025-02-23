package com.payments.reconciler.util;

import com.opencsv.bean.AbstractBeanField;
import com.opencsv.exceptions.CsvConstraintViolationException;
import com.opencsv.exceptions.CsvDataTypeMismatchException;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;

/**
 *This class is custom converter for opencsv that converts
 *a String date in the format of "dd-MM-yyyy" into a LocalDate Object.
 *It extends AbstractBeanField which facilitates automatic conversion while parsing CSV files.
 */
public class LocalDateConverter extends AbstractBeanField<LocalDate, String> {

    //Defining a DateTimeFormatter to parse date Strings that come in the format "dd-MM-yyyy"
    private static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("dd-MM-yyyy");

    @Override
    protected LocalDate convert(String dateString)
            throws CsvDataTypeMismatchException, CsvConstraintViolationException, DateTimeParseException {
        return LocalDate.parse(dateString, formatter);
    }

}
