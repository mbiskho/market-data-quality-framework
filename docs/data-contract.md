# Data contract

The input is UTF-8 CSV with a header containing `timestamp`, `open`, `high`,
`low`, `close`, and `volume`. Extra columns are ignored. Timestamps use
ISO-8601; timezone-naive values are treated as UTC, and offset-aware timestamps
are converted to UTC before checking order, uniqueness, and spacing. Prices
must be finite and positive, volume finite and non-negative, and the OHLC
envelope must satisfy `low <= open, close <= high`.

The configured interval defaults to one minute. A longer spacing produces a
warning; this framework does not infer exchange calendars, holidays, or session
boundaries. Duplicate times, malformed values, invalid prices, and incomplete
records are errors. The score is an illustrative weighted diagnostic—not a
certification: 40% completeness, 40% row validity, and 20% timestamp
uniqueness. All sample observations are synthetic.
