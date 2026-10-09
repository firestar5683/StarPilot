package link.firestar.galaxybt;

import java.net.URI;
import java.util.Set;

final class RequestPolicy {
    static final String ORIGIN = "https://appassets.androidplatform.net";
    static final String CATALOG = "/assets/components/tools/device_settings_layout.json?v=settings-tier-1";
    static boolean local(URI uri) {
        return "https".equals(uri.getScheme()) && "appassets.androidplatform.net".equals(uri.getHost())
                && (uri.getPort() == -1 || uri.getPort() == 443) && uri.getUserInfo() == null;
    }
    static void validate(String target, String method) throws Exception {
        if (target.length() > 8192 || !new java.util.HashSet<>(java.util.Arrays.asList("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE")).contains(method)) throw new IllegalArgumentException("Unsupported Galaxy request.");
        URI uri = new URI(target); String path = uri.getPath();
        if (uri.isAbsolute() || uri.getRawAuthority() != null || uri.getFragment() != null || path == null || !path.startsWith("/")
                || path.contains("\\") || path.contains("//") || path.contains("%") || path.chars().anyMatch(c -> c < 32) || target.chars().anyMatch(c -> c < 32)) throw new IllegalArgumentException("Invalid Galaxy path.");
        for (String part : path.split("/")) if (part.equals(".") || part.equals("..")) throw new IllegalArgumentException("Invalid path segments.");
        if (!(path.startsWith("/api/") || path.equals("/assets/components/tools/device_settings_layout.json"))) throw new IllegalArgumentException("Path is outside the Galaxy API.");
    }
}
