import { Activity } from "@/types/strava";
import { formatDistance, formatTime, formatSpeed, formatDate } from "@/lib/utils";

interface ActivityTableProps {
  activities: Activity[];
  className?: string;
}

const getActivityTypeColor = (type: string) => {
  const colors = {
    Run: "bg-blue-100 text-blue-800 border-blue-200",
    Ride: "bg-green-100 text-green-800 border-green-200",
    Walk: "bg-purple-100 text-purple-800 border-purple-200",
    Swim: "bg-cyan-100 text-cyan-800 border-cyan-200",
    default: "bg-slate-100 text-slate-800 border-slate-200"
  };
  return colors[type as keyof typeof colors] || colors.default;
};

export function ActivityTable({ activities, className = "" }: ActivityTableProps) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-slate-900">Recent Activities</h3>
          <div className="h-px bg-gradient-to-r from-blue-500 to-transparent w-24"></div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-4 px-4 font-semibold text-slate-700 uppercase tracking-wide text-xs">Date</th>
                <th className="text-left py-4 px-4 font-semibold text-slate-700 uppercase tracking-wide text-xs">Activity</th>
                <th className="text-left py-4 px-4 font-semibold text-slate-700 uppercase tracking-wide text-xs">Type</th>
                <th className="text-left py-4 px-4 font-semibold text-slate-700 uppercase tracking-wide text-xs">Distance</th>
                <th className="text-left py-4 px-4 font-semibold text-slate-700 uppercase tracking-wide text-xs">Duration</th>
                <th className="text-left py-4 px-4 font-semibold text-slate-700 uppercase tracking-wide text-xs">Avg Speed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {activities.slice(0, 10).map((activity, index) => (
                <tr key={activity.id} className="group hover:bg-blue-50/30 transition-colors duration-150">
                  <td className="py-4 px-4 text-slate-600 text-sm">{formatDate(activity.start_date_local)}</td>
                  <td className="py-4 px-4">
                    <div className="font-semibold text-slate-900 group-hover:text-blue-700 transition-colors duration-150">
                      {activity.name}
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium border ${getActivityTypeColor(activity.type)}`}>
                      {activity.type}
                    </span>
                  </td>
                  <td className="py-4 px-4 text-slate-700 font-medium">{formatDistance(activity.distance)}</td>
                  <td className="py-4 px-4 text-slate-700 font-medium">{formatTime(activity.moving_time)}</td>
                  <td className="py-4 px-4 text-slate-700 font-medium">{formatSpeed(activity.average_speed)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}