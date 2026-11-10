export function BrandMark() {
  return (
    <div className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 48 48" role="presentation">
        <rect
          x="1"
          y="1"
          width="46"
          height="46"
          rx="14"
          fill="currentColor"
          opacity="0.14"
        />
        <path d="M12 35V24h6v11h-6Zm9 0V17h6v18h-6Zm9 0v-8h6v8h-6Z" fill="currentColor" />
        <path
          d="M11 14.5 20 9l7 3.5L37 7"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="brand-mark__text">FinTrack-5</span>
    </div>
  )
}
