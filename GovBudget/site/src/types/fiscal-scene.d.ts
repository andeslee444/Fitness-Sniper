import type { DetailedHTMLProps, HTMLAttributes } from "react";

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "fiscal-scene": DetailedHTMLProps<HTMLAttributes<HTMLElement>, HTMLElement> & {
        src: string;
        subject: string;
        selected: string;
        blueprint: string;
        reset: string;
        topics: string;
      };
    }
  }
}
