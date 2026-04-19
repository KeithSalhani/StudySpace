export default function VisuallyHidden({ children, as: Component = "span", ...props }) {
  return (
    <Component className="sr-only" {...props}>
      {children}
    </Component>
  );
}
