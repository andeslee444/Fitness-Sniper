import type { DetailedHTMLProps, HTMLAttributes } from "react";
import type { F15SceneElement } from "@/components/f15-model";

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "f15-family-scene": DetailedHTMLProps<HTMLAttributes<F15SceneElement>, F15SceneElement> & {
        variant?: string;
        compare?: string;
        selected?: string;
        blueprint?: string;
        conformal?: string;
      };
    }
  }
}
