import { apiServer, type DashboardSummary } from "@/lib/api";
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

export default async function DashboardPage() {
  const session = await auth();
  if (!session?.user?.id) redirect("/auth/login");

  const data = await getDashboard();

  return <DashboardClient data={data} />;
}
