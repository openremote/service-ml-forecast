import path from 'path';
import rspack from '@rspack/core';
import { fileURLToPath } from 'url';
import process from 'process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isProduction = process.env.NODE_ENV === 'production';
const rootPath = process.env.ML_WEB_ROOT_PATH;
const serviceUrl = process.env.ML_SERVICE_URL || 'http://localhost:8000'; // Default to default service backend
const keycloakUrl = process.env.ML_OR_KEYCLOAK_URL || 'http://localhost:8081/auth'; // Default to openremote keycloak address
const openremoteUrl = process.env.ML_OR_URL || 'http://localhost:8080';

export default {
    mode: isProduction ? 'production' : 'development',
    devtool: isProduction ? 'source-map' : 'eval-source-map',
    entry: {
        main: './src/index.ts'
    },
    output: {
        filename: `bundle.[contenthash].js`,
        clean: true,
        path: path.resolve(__dirname, 'dist'),
        publicPath: rootPath ? rootPath : '/'
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
            template: './index.html',
            templateParameters: {
                // prefix hrefs inside the index.html
                templateRootPath: rootPath ? rootPath : ''
            }
        }),
        new rspack.CopyRspackPlugin({
            patterns: [{ from: 'assets', to: 'assets' }]
        }),
        new rspack.DefinePlugin({
            'process.env.ML_SERVICE_URL': JSON.stringify(serviceUrl),
            'process.env.ML_OR_KEYCLOAK_URL': JSON.stringify(keycloakUrl),
            'process.env.ML_OR_URL': JSON.stringify(openremoteUrl)
        })
    ],
    devServer: {
        port: 8001,
        historyApiFallback: true,
        hot: true,
        watchFiles: ['/**/*'],
        headers: {
            'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
            Pragma: 'no-cache',
            Expires: '0'
        }
    }
};
