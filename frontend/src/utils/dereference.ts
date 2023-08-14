/* Copyright 2023 Marimo. All rights reserved. */

// Dereferences a ref that should not be null; throws if the value is null
export function derefNotNull<T>(ref: React.RefObject<T | null>): T {
  const value = ref.current;
  if (value === null) {
    throw new ReferenceError("Attempting to dereference null object.");
  }
  return value;
}
