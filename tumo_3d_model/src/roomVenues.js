/** Maps Three.js room slugs to SpaceFlow venue names used by the AI layout engine. */
export const ROOM_VENUE_NAMES = {
  'blue-box': 'Blue Room',
  'orange-box': 'Orange Room',
  'lime-green-box': 'Green Room',
  'dark-green-box': 'Yellow Room',
};

export function getVenueNameForRoom(roomId) {
  return ROOM_VENUE_NAMES[roomId] || null;
}

export function isAiSupportedRoom(roomId) {
  return Boolean(roomId && ROOM_VENUE_NAMES[roomId]);
}
