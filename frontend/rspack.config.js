import path from 'path'
import rspack from '@rspack/core'
import { fileURLToPath } from 'url'
import process from 'process'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const isProduction = process.env.NODE_ENV === 'production'

export default {
    mode: isProduction ? 'production' : 'development',
    devtool: isProduction ? 'source-map' : 'eval-source-map',
    entry: {
        main: './src/index.ts'
    },
    output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, 'dist'),
        publicPath: '/'
    },
    resolve: {
        extensions: ['.ts', '.js']
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
                                decorators: true
                            },
                            transform: {
                                legacyDecorator: true,
                                decoratorMetadata: true,
                                useDefineForClassFields: false
                            }
                        }
                    }
                }
            },
            {
                test: /\.css$/,
                type: 'asset/source'
            }
        ]
    },
    plugins: [
        new rspack.HtmlRspackPlugin({
            template: './index.html'
        }),
        new rspack.CopyRspackPlugin({
            patterns: [{ from: 'static', to: 'static' }]
        }),
        new rspack.DefinePlugin({
            'process.env.ML_SERVICE_URL': JSON.stringify(process.env.ML_SERVICE_URL || '')
        })
    ],
    devServer: {
        port: 8001,
        historyApiFallback: true,
        hot: true,
        watchFiles: ['/**/*'],
        compress: true
    }
}
