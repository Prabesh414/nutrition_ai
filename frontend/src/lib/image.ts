/**
 * Profile image handling.
 *
 * Images are stored as base64 data URLs on the profile row, so an unbounded
 * upload becomes an unbounded database column that is returned on every login.
 * Oversized images are downscaled client-side and rejected if still too large;
 * the server enforces the same ceiling independently.
 */
export const MAX_PROFILE_IMAGE_BYTES = 512 * 1024;
const MAX_DIMENSION = 512;
const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp'];

function dataUrlBytes(dataUrl: string): number {
  return new Blob([dataUrl]).size;
}

function loadImage(objectUrl: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('That file could not be read as an image.'));
    image.src = objectUrl;
  });
}

/** Read a file, downscale it to at most 512px, and return a JPEG data URL. */
export async function readImageAsDataUrl(file: File): Promise<string> {
  if (!ALLOWED_TYPES.includes(file.type)) {
    throw new Error('Please choose a PNG, JPEG or WebP image.');
  }

  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await loadImage(objectUrl);

    const scale = Math.min(1, MAX_DIMENSION / Math.max(image.width, image.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(image.width * scale));
    canvas.height = Math.max(1, Math.round(image.height * scale));

    const context = canvas.getContext('2d');
    if (!context) throw new Error('Your browser could not process that image.');
    context.drawImage(image, 0, 0, canvas.width, canvas.height);

    // Step the quality down until it fits, rather than failing outright.
    for (const quality of [0.85, 0.7, 0.55, 0.4]) {
      const dataUrl = canvas.toDataURL('image/jpeg', quality);
      if (dataUrlBytes(dataUrl) <= MAX_PROFILE_IMAGE_BYTES) return dataUrl;
    }

    throw new Error(
      `That image is too large even after compression. Please choose one under ${Math.round(
        MAX_PROFILE_IMAGE_BYTES / 1024,
      )} KB.`,
    );
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}
