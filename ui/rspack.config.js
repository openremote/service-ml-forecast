import path from 'path';
import rspack from '@rspack/core';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default {
  mode: 'development',
  entry: {
    main: './src/index.ts',
  },
  output: {
    filename: 'bundle.js',
    path: path.resolve(__dirname, 'dist'),
    publicPath: '/',
  },
  resolve: {
    extensions: ['.ts', '.js'],
  },
  module: {
    rules: [
      {
        test: /\.ts$/,
        use: {
          loader: 'builtin:swc-loader',
          options: {

            jsc: {
              parser: {
                syntax: 'typescript',
                decorators: true,
              },
              transform: {
                legacyDecorator: true,
                decoratorMetadata: true,
                useDefineForClassFields: false,
              }
            },
          },
        },
      },
      {
        test: /\.css$/,
        type: 'asset/source',
      },
    ],
  },
  plugins: [
    new rspack.HtmlRspackPlugin({
      template: './index.html',
    }),
    new rspack.CopyRspackPlugin({
      patterns: [
        { from: 'static', to: 'static' },
      ],
    }),
  ],
  devServer: {
    port: 8001,
    historyApiFallback: true,
    hot: true,
    watchFiles: ['/**/*'],
  },
}; 