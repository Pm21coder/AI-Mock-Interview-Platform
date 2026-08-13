import Link from 'next/link';

export default function FeatureGateComponent({
  featureName,
  userTier,
  requiredTier,
  children,
  fallback = null,
}) {
  const tierHierarchy = {
    free: 0,
    basic: 1,
    pro: 2,
  };

  const userTierLevel = tierHierarchy[userTier] || 0;
  const requiredTierLevel = tierHierarchy[requiredTier] || 1;

  const hasAccess = userTierLevel >= requiredTierLevel;

  if (hasAccess) {
    return children;
  }

  if (fallback) {
    return fallback;
  }

  return (
    <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-6">
      <div className="text-center">
        <svg
          className="mx-auto h-12 w-12 text-yellow-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
          />
        </svg>
        <h3 className="mt-4 text-lg font-semibold text-yellow-900">
          {featureName} is a Premium Feature
        </h3>
        <p className="mt-2 text-sm text-yellow-700">
          Upgrade to the <span className="font-semibold capitalize">{requiredTier}</span> plan to
          access this feature.
        </p>
        <Link
          href="/subscription"
          className="mt-4 inline-block rounded-lg bg-yellow-600 px-6 py-2 font-semibold text-white hover:bg-yellow-700"
        >
          View Plans
        </Link>
      </div>
    </div>
  );
}
