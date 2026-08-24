export default function BrandMark({ size = 36, centerFill = "#121826" }) {
  const height = Math.round(size * 0.8);

  return (
    <svg
      width={size}
      height={height}
      viewBox="0 0 100 80"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="shrink-0"
      aria-hidden="true"
    >
      <rect x="22" y="10" width="12" height="60" fill="#1c7ec2" />
      <rect x="44" y="10" width="12" height="60" fill="#1c7ec2" />
      <rect x="66" y="10" width="12" height="60" fill="#1c7ec2" />
      <path
        d="M 5,38 C 15,38 15,48 25,48 H 36 C 44,48 44,40 50,40 C 56,40 56,48 64,48 H 75 C 85,48 85,62 95,62"
        stroke="#1ce5b2"
        strokeWidth="5"
        fill="none"
        strokeLinecap="round"
      />
      <circle cx="5" cy="38" r="5" fill="#1ce5b2" />
      <circle cx="5" cy="38" r="2.2" fill={centerFill} />
      <circle cx="95" cy="62" r="5" fill="#1ce5b2" />
      <circle cx="95" cy="62" r="2.2" fill={centerFill} />
      <circle cx="50" cy="40" r="10" fill={centerFill} stroke="#1ce5b2" strokeWidth="5" />
    </svg>
  );
}
