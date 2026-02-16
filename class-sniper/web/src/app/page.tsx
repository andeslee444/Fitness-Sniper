import Link from 'next/link';

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
      <main className="flex max-w-2xl flex-col items-center gap-8 px-6 text-center">
        <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
          Class Sniper
        </h1>
        <p className="max-w-lg text-lg text-zinc-400">
          Auto-book competitive fitness classes before they fill up. Barry&apos;s,
          Aarmy, SLT, and more.
        </p>
        <div className="flex gap-4">
          <Link
            href="/signup"
            className="rounded-full bg-white px-6 py-3 font-semibold text-black transition hover:bg-zinc-200"
          >
            Get Started
          </Link>
          <Link
            href="/login"
            className="rounded-full border border-zinc-700 px-6 py-3 font-semibold transition hover:bg-zinc-900"
          >
            Log In
          </Link>
        </div>

        <div className="mt-16 grid gap-6 sm:grid-cols-3">
          {[
            { title: 'Set Targets', desc: 'Choose studio, day, time, and preferred spot.' },
            { title: 'Auto-Book', desc: 'Our worker books the instant classes open.' },
            { title: 'Get Notified', desc: 'Email confirmation with your booked spot.' },
          ].map((f) => (
            <div key={f.title} className="rounded-xl border border-zinc-800 p-6 text-left">
              <h3 className="mb-2 text-lg font-semibold">{f.title}</h3>
              <p className="text-sm text-zinc-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
