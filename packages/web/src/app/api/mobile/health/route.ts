import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({ 
    status: 'ok', 
    message: 'Mobile API is running',
    timestamp: new Date().toISOString()
  });
}