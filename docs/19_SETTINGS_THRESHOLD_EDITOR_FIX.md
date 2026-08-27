# Settings Threshold Editor Fix – Video 11:20

## Reported behaviour

Threshold values reverted while being edited, the native number-field arrows were difficult to use, and there was no useful confirmation that a value had been persisted.

## Root cause

The application refreshes live telemetry every three seconds. Thresholds were incorrectly included in the same polling request, and every response reset the editor draft to the last stored database value.

## Fix

- Thresholds are now loaded separately from live telemetry polling.
- Unsaved edits remain untouched until the operator saves or reloads the page.
- Native number spinners were replaced with large minus/value/plus controls.
- Temperature and humidity step by 0.5; binary sensors step by 1.
- Operators can still type values directly.
- Every sensor has its own `Save this threshold` action.
- Successful persistence displays the exact saved rule; errors are displayed on the same card.
