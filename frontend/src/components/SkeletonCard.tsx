
export function SkeletonCard() {
  return (
    <div className="blueprint-card animate-pulse flex overflow-hidden min-h-[180px]">
      <div className="w-1.5 bg-[rgba(199,211,234,0.18)] flex-shrink-0" />
      <div className="flex flex-col md:flex-row flex-1">
        <div className="flex-[2] p-5 flex flex-col justify-between border-r border-[rgba(186,215,247,0.12)]">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="h-4 w-32 bg-[rgba(199,211,234,0.12)] rounded"></div>
              <div className="h-4 w-20 bg-[rgba(199,211,234,0.12)] rounded-md"></div>
            </div>
            <div className="h-6 bg-[rgba(199,211,234,0.14)] rounded w-3/4 mb-3"></div>
            <div className="space-y-2">
              <div className="h-3 bg-[rgba(199,211,234,0.12)] rounded w-1/2"></div>
              <div className="h-3 bg-[rgba(199,211,234,0.12)] rounded w-1/3"></div>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <div className="h-6 w-20 bg-[rgba(199,211,234,0.08)] rounded border border-[rgba(186,215,247,0.12)]"></div>
            <div className="h-6 w-20 bg-[rgba(199,211,234,0.08)] rounded border border-[rgba(186,215,247,0.12)]"></div>
          </div>
        </div>
        <div className="flex-1 p-5 bg-[rgba(5,6,15,0.28)] flex flex-col justify-between items-end">
          <div className="w-24 h-4 bg-[rgba(199,211,234,0.12)] rounded mb-2"></div>
          <div className="w-32 h-8 bg-[rgba(199,211,234,0.18)] rounded mb-4"></div>
          <div className="w-full space-y-2">
            <div className="h-3 bg-[rgba(199,211,234,0.12)] rounded w-full"></div>
            <div className="h-2 bg-[rgba(199,211,234,0.12)] rounded w-2/3"></div>
          </div>
          <div className="w-full h-10 bg-[rgba(199,211,234,0.14)] rounded mt-4"></div>
        </div>
      </div>
    </div>
  )
}

export function SkeletonStats() {
  return (
    <div className="blueprint-card p-6 animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-12 w-12 bg-[rgba(199,211,234,0.12)] rounded"></div>
        <div className="h-4 bg-[rgba(199,211,234,0.12)] rounded w-16"></div>
      </div>
      <div className="h-2 bg-[rgba(199,211,234,0.12)] rounded-full mb-3"></div>
      <div className="h-10 bg-[rgba(199,211,234,0.14)] rounded mb-1"></div>
      <div className="h-4 bg-[rgba(199,211,234,0.12)] rounded w-2/3"></div>
    </div>
  )
}







