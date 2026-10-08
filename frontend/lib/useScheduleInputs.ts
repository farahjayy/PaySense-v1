"use client";
// Shared state for the two BNPL forms (Risk Checker, Add plan): provider, purchase date and
// the estimated first payment date (follows the provider's rule until the user edits it).
import { useState } from "react";

import { todayISO } from "@/lib/format";
import { checkoutInstalments, defaultFirstPaymentDate } from "@/lib/schedule";

export function useScheduleInputs(initialProvider: string) {
  const [provider, setProviderState] = useState(initialProvider);
  const [purchaseDate, setPurchaseDateState] = useState(todayISO());
  // "" means "follow the provider's rule"; anything else is the user's own first due date.
  const [firstPaymentOverride, setFirstPaymentOverride] = useState("");

  const firstPaymentDate = firstPaymentOverride || defaultFirstPaymentDate(provider, purchaseDate);
  const checkoutCount = checkoutInstalments(provider, firstPaymentDate, purchaseDate);

  // Changing anything the rule depends on hands the first due date back to the rule.
  const setProvider = (value: string) => {
    setProviderState(value);
    setFirstPaymentOverride("");
  };
  const setPurchaseDate = (value: string) => {
    setPurchaseDateState(value);
    setFirstPaymentOverride("");
  };

  return {
    provider,
    purchaseDate,
    firstPaymentDate,
    firstPaymentOverride,
    checkoutCount,
    setProvider,
    setPurchaseDate,
    setFirstPaymentDate: setFirstPaymentOverride,
  };
}
