import { apiServer, type DashboardSummary, type InsightsResponse } from "@/lib/api";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import DashboardClient from "./DashboardClient";

async function getDashboard(): Promise<DashboardSummary | null> {
  try {
    return await apiServer<DashboardSummary>("/api/analytics/dashboard");
  } catch {
    return null;
  }
}

async function getInsights(): Promise<InsightsResponse | null> {
  try {
    return await apiServer<InsightsResponse>("/api/analytics/insights");
  } catch {
    return null;
  }
}

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user?.id) redirect("/auth/login");

  const [data, insights] = await Promise.all([getDashboard(), getInsights()]);

  return <DashboardClient data={data} insights={insights} />;
}
