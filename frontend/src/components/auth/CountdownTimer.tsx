import { useState, useEffect, useCallback } from 'react';

interface CountdownTimerProps {
  seconds: number;
  onExpired?: () => void;
  className?: string;
}

export function CountdownTimer({ seconds, onExpired, className }: CountdownTimerProps) {
  const [remaining, setRemaining] = useState(seconds);

  useEffect(() => {
    setRemaining(seconds);
  }, [seconds]);

  const handleExpired = useCallback(() => {
    onExpired?.();
  }, [onExpired]);

  useEffect(() => {
    if (remaining <= 0) {
      handleExpired();
      return;
    }

    const timer = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [remaining, handleExpired]);

  const minutes = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const display = `${minutes}:${secs.toString().padStart(2, '0')}`;

  return (
    <span className={className}>
      {display}
    </span>
  );
}

/**
 * Hook version for use in components that need the countdown value
 */
export function useCountdown(seconds: number, onExpired?: () => void) {
  const [remaining, setRemaining] = useState(seconds);

  useEffect(() => {
    setRemaining(seconds);
  }, [seconds]);

  const handleExpired = useCallback(() => {
    onExpired?.();
  }, [onExpired]);

  useEffect(() => {
    if (remaining <= 0) {
      handleExpired();
      return;
    }

    const timer = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [remaining, handleExpired]);

  const minutes = Math.floor(remaining / 60);
  const secs = remaining % 60;
  const display = `${minutes}:${secs.toString().padStart(2, '0')}`;

  return { remaining, display, isExpired: remaining <= 0 };
}
