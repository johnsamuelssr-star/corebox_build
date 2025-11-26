import React from "react";

function Login() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 text-slate-100">
      <div className="max-w-md w-full bg-slate-950 border border-slate-800 rounded-2xl p-8 flex flex-col space-y-6">
        <div className="space-y-1">
          <div className="text-sm text-slate-400">CoreBox Systems</div>
          <h1 className="text-2xl font-semibold">Sign in to your account</h1>
          <p className="text-sm text-slate-400">
            Owner access for Mindfull Learning.
          </p>
        </div>

        <div className="flex flex-col space-y-4">
          <div className="flex flex-col space-y-1">
            <label className="text-sm text-slate-300" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="you@example.com"
            />
          </div>

          <div className="flex flex-col space-y-1">
            <label className="text-sm text-slate-300" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="••••••••"
            />
          </div>
        </div>

        <button className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2 rounded-lg text-sm">
          Sign in
        </button>

        <p className="text-xs text-slate-500 text-center">
          This is a demo login screen. Authentication is not yet connected.
        </p>
      </div>
    </div>
  );
}

export default Login;
