
export type Platform =
  | "youtube"
  | "instagram"
  | "facebook"
  | "x"
  | "unknown";

export interface PlatformResult {
  platform: Platform;
  valid: boolean;
  videoId?: string;
  normalizedUrl?: string;
  message: string;
}

export function detectPlatform(input: string): PlatformResult {
  try {
    const url = new URL(input.trim());

    const host = url.hostname
      .toLowerCase()
      .replace(/^www\./, "");

    // YouTube
    if (
      host === "youtube.com" ||
      host === "m.youtube.com" ||
      host === "youtu.be" ||
      host === "youtube-nocookie.com"
    ) {
      let videoId = "";

      if (host === "youtu.be") {
        videoId = url.pathname.split("/").filter(Boolean)[0] || "";
      } else {
        videoId =
          url.searchParams.get("v") ||
          url.pathname.match(
            /^\/(?:shorts|embed|live)\/([a-zA-Z0-9_-]{11})/
          )?.[1] ||
          "";
      }

      if (!/^[a-zA-Z0-9_-]{11}$/.test(videoId)) {
        return {
          platform: "youtube",
          valid: false,
          message: "Please enter a valid YouTube video URL.",
        };
      }

      return {
        platform: "youtube",
        valid: true,
        videoId,
        normalizedUrl: `https://www.youtube.com/watch?v=${videoId}`,
        message: "YouTube video recognized.",
      };
    }

    // Instagram
    if (
      host === "instagram.com" ||
      host === "instagr.am"
    ) {
      const match = url.pathname.match(
        /^\/(?:p|reel|reels|tv)\/([a-zA-Z0-9_-]+)/
      );

      return {
        platform: "instagram",
        valid: Boolean(match),
        normalizedUrl: url.toString(),
        message: match
          ? "Instagram media URL recognized."
          : "Please enter an Instagram post or reel URL.",
      };
    }

    // Facebook
    if (
      host === "facebook.com" ||
      host === "fb.watch" ||
      host === "m.facebook.com"
    ) {
      return {
        platform: "facebook",
        valid: true,
        normalizedUrl: url.toString(),
        message: "Facebook URL recognized.",
      };
    }

    // X / Twitter
    if (
      host === "x.com" ||
      host === "twitter.com"
    ) {
      const match = url.pathname.match(
        /^\/[^/]+\/status\/(\d+)/
      );

      return {
        platform: "x",
        valid: Boolean(match),
        normalizedUrl: url.toString(),
        message: match
          ? "X post URL recognized."
          : "Please enter a valid X post URL.",
      };
    }

    return {
      platform: "unknown",
      valid: false,
      message: "This platform is not supported.",
    };

  } catch {
    return {
      platform: "unknown",
      valid: false,
      message: "Please enter a valid URL starting with https://",
    };
  }
}
