import { Scale } from "lucide-react";

/** SaulGPT logo: scales of justice inside a soft blue→violet ring. */
export default function BrandMark({ size = 36, className = "" }) {
  return (
    <div
      className={`relative shrink-0 rounded-xl flex items-center justify-center bg-gradient-to-br from-brand-500 to-violet-600 text-white shadow-md shadow-brand-500/25 ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <Scale style={{ width: size * 0.5, height: size * 0.5 }} strokeWidth={2.2} />
    </div>
  );
}
