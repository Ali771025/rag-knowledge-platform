import { useCallback, useState } from "react";

export function useErrorBoundaryReset() {
  const [resetToken, setResetToken] = useState(0);

  const reset = useCallback(() => {
    setResetToken((value) => value + 1);
  }, []);

  return {
    resetToken,
    reset
  };
}
