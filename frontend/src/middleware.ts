import { auth } from "@/auth";
import { NextResponse } from "next/server";

const PUBLIC_PREFIXES = ["/auth", "/api/auth", "/_next", "/favicon"];

export default auth((req) => {
  const { pathname } = req.nextUrl;
  const isPublic = PUBLIC_PREFIXES.some((p) => pathname.startsWith(p));
  if (isPublic) return NextResponse.next();

  if (!req.auth) {
    const loginUrl = new URL("/auth/login", req.nextUrl.origin);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
});

export const config = {
  // Match all routes except Next internals & static files.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
