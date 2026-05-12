import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { apiServer } from "@/lib/api";
import type { PlatformConnection } from "@/lib/api";
import { ConnectionsClient } from "./_client";

export default async function ConnectionsPage() {
  const session = await auth();
  if (!session) redirect("/auth/login");

  const connections = await apiServer<PlatformConnection[]>("/api/connections");

  return <ConnectionsClient initialConnections={connections} />;
}
