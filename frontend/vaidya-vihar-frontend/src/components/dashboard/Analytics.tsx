import AnalyticsDashboard from '../analytics/AnalyticsDashboard'

interface AnalyticsProps {
  branchId?: number
}

export default function Analytics({ branchId }: AnalyticsProps) {
  return <AnalyticsDashboard forcedBranchId={branchId} />
}
