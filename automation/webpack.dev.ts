module.exports = {
  resolve: {
    fallback: {
      "vm": require.resolve("vm-browserify"),
      "crypto": require.resolve("crypto-browserify"),
      "stream": require.resolve("stream-browserify"),
      "buffer": require.resolve("buffer/"),
      "util": require.resolve("util/"),
      "assert": require.resolve("assert/"),
      "path": require.resolve("path-browserify"),
      "url": require.resolve("url/"),
      "process": require.resolve("process/browser"),
      "zlib": require.resolve("browserify-zlib"),
      "querystring": require.resolve("querystring-es3")
    }
  },
  plugins: [
    new webpack.ProvidePlugin({
      process: 'process/browser',
      Buffer: ['buffer', 'Buffer']
    })
  ]
} 