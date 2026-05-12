import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { apiServer } from "@/lib/api";
import type { PlatformConnection } from "@/lib/api";
import { ConnectionsClient } from "./_client";

export default async function ConnectionsPage() {
  const session = await auth();
  if (!session) redirect("/auth/login");

  let connections: PlatformConnection[] = [];
  try {
    connections = await apiServer<PlatformConnection[]>("/api/connections");
  } catch {
    // backend unreachable or table missing — render page with empty state
  }

  return <ConnectionsClient initialConnections={connections} />;
}
