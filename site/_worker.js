// ILANG
// TYPE:worker ROLE:canonical-host-redirect
// ::RULE{非规范主机名一律 301 到主域名⇒不许留两个地址并存}
// ::RULE{主域名请求必须原样交给静态资源⇒漏了这行整站会 404}
// ::BOUNDARY{never:在这里改页面内容|scope:file}
const CANONICAL_HOST = "vpsdealsradar.com";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname !== CANONICAL_HOST) {
      const target = new URL(url.pathname + url.search, `https://${CANONICAL_HOST}`);
      return Response.redirect(target.toString(), 301);
    }
    return env.ASSETS.fetch(request);
  },
};
