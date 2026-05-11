import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { apiServer } from "@/lib/api";
import { ProfileClient, type ProfileData } from "./_client";

export default async function ProfilePage() {
  const session = await auth();
  if (!session) redirect("/auth/login");

  const profile = await apiServer<ProfileData>("/api/me");

  return <ProfileClient profile={profile} />;
}
