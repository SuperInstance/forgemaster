// src/plato/bridge.ts — PLATO HTTP REST bridge

export interface PlatoRoom {
  room: string;
  tiles: PlatoTile[];
}

export interface PlatoTile {
  title: string;
  content: string;
  tags?: string[];
  timestamp?: string;
}

export class PlatoHttpBridge {
  private baseUrl: string;
  private roomPrefix: string;

  constructor(baseUrl: string, roomPrefix: string = 'jester') {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.roomPrefix = roomPrefix;
  }

  /**
   * Push a session summary as a tile to a PLATO room.
   */
  async pushTile(
    room: string,
    title: string,
    content: string,
    tags?: string[]
  ): Promise<{ success: boolean; error?: string }> {
    const fullRoom = `${this.roomPrefix}/${room}`;
    const url = `${this.baseUrl}/api/rooms/${encodeURIComponent(fullRoom)}/tiles`;

    const body: PlatoTile = {
      title,
      content,
      tags: tags ?? ['jester', 'ideation'],
      timestamp: new Date().toISOString(),
    };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'unknown error');
        return { success: false, error: `PLATO API error: ${response.status} — ${errorText}` };
      }

      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { success: false, error: `PLATO connection error: ${message}` };
    }
  }

  /**
   * Pull context from a PLATO room to prime ideation.
   */
  async pullRoomContext(
    room: string,
    limit: number = 5
  ): Promise<{ success: boolean; tiles?: PlatoTile[]; error?: string }> {
    const fullRoom = `${this.roomPrefix}/${room}`;
    const url = `${this.baseUrl}/api/rooms/${encodeURIComponent(fullRoom)}/tiles?limit=${limit}`;

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'unknown error');
        return { success: false, error: `PLATO API error: ${response.status} — ${errorText}` };
      }

      const data = (await response.json()) as { tiles: PlatoTile[] };
      return { success: true, tiles: data.tiles ?? [] };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { success: false, error: `PLATO connection error: ${message}` };
    }
  }

  /**
   * List rooms the jester has access to.
   */
  async listRooms(): Promise<{ success: boolean; rooms?: string[]; error?: string }> {
    const url = `${this.baseUrl}/api/rooms?prefix=${encodeURIComponent(this.roomPrefix)}`;

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        return { success: false, error: `PLATO API error: ${response.status}` };
      }

      const data = (await response.json()) as { rooms: string[] };
      return { success: true, rooms: data.rooms ?? [] };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { success: false, error: `PLATO connection error: ${message}` };
    }
  }

  /**
   * Check if the PLATO server is reachable.
   */
  async healthCheck(): Promise<{ alive: boolean; error?: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });
      return { alive: response.ok };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { alive: false, error: message };
    }
  }
}
