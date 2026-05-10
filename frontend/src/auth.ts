import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      fullName?: string | null;
    } & DefaultSession["user"];
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    userId?: string;
    fullName?: string | null;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      name: "OptiPrice",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Şifre", type: "password" },
      },
      async authorize(credentials) {
        const email = String(credentials?.email ?? "").trim().toLowerCase();
        const password = String(credentials?.password ?? "");
        if (!email || !password) return null;

        const res = await fetch(`${BACKEND_URL}/api/auth/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
          cache: "no-store",
        });
        if (!res.ok) return null;
        const user = (await res.json()) as {
          id: number;
          email: string;
          full_name: string | null;
        };
        return {
          id: String(user.id),
          email: user.email,
          name: user.full_name ?? undefined,
        };
      },
    }),
  ],
  pages: {
    signIn: "/auth/login",
  },
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.userId = user.id;
        token.fullName = user.name ?? null;
      }
      return token;
    },
    async session({ session, token }) {
      if (token.userId) {
        session.user.id = token.userId;
        session.user.fullName = token.fullName ?? null;
      }
      return session;
    },
  },
});
