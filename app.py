from flask import Flask, render_template, jsonify, request
from data_fetcher import COVIDDataFetcher
import plotly.graph_objs as go
import plotly.utils
import json
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
fetcher = COVIDDataFetcher()

@app.route('/')
def index():
    """Render the main dashboard page"""
    # Get country list for dropdown
    countries = fetcher.get_country_list()
    country_names = [{'name': 'Global', 'code': 'global'}] + countries
    
    return render_template('index.html', countries=country_names)

@app.route('/api/global_stats')
def get_global_stats():
    """API endpoint for global statistics"""
    stats = fetcher.get_global_stats()
    if stats:
        return jsonify(stats)
    return jsonify({'error': 'Failed to fetch data'}), 500

@app.route('/api/country_stats')
def get_country_stats():
    """API endpoint for country statistics"""
    country = request.args.get('country', '')
    if country:
        data = fetcher.get_country_stats(country)
        if data:
            if isinstance(data, list) and len(data) > 0:
                stats = data[0]
            elif isinstance(data, dict):
                stats = data
            else:
                return jsonify({'error': 'No data available'}), 404
                
            return jsonify({
                'country': stats.get('country', ''),
                'total_cases': stats.get('cases', 0),
                'total_deaths': stats.get('deaths', 0),
                'total_recovered': stats.get('recovered', 0),
                'active_cases': stats.get('active', 0),
                'critical_cases': stats.get('critical', 0),
                'total_tests': stats.get('tests', 0),
                'cases_per_million': stats.get('casesPerOneMillion', 0),
                'deaths_per_million': stats.get('deathsPerOneMillion', 0),
                'population': stats.get('population', 0)
            })
    
    # Return all countries if no specific country requested
    data = fetcher.get_country_stats()
    if data:
        return jsonify(data[:50])  # Limit to top 50 countries
    return jsonify({'error': 'Failed to fetch data'}), 500

@app.route('/api/historical_data')
def get_historical_data():
    """API endpoint for historical data"""
    country = request.args.get('country', 'all')
    days = int(request.args.get('days', 30))
    
    data = fetcher.get_historical_data(country, days)
    if data is not None and isinstance(data, pd.DataFrame):
        # Convert DataFrame to JSON
        return jsonify({
            'dates': data['date'].dt.strftime('%Y-%m-%d').tolist(),
            'cases': data['cases'].tolist(),
            'deaths': data['deaths'].tolist(),
            'recovered': data['recovered'].tolist() if 'recovered' in data.columns else [],
            'new_cases': data['new_cases'].tolist() if 'new_cases' in data.columns else [],
            'new_deaths': data['new_deaths'].tolist() if 'new_deaths' in data.columns else []
        })
    return jsonify({'error': 'Failed to fetch historical data'}), 500

@app.route('/api/chart_data')
def get_chart_data():
    """Generate chart data for Plotly visualizations"""
    country = request.args.get('country', 'all')
    days = int(request.args.get('days', 30))
    
    data = fetcher.get_historical_data(country, days)
    if data is None:
        return jsonify({'error': 'No data available'}), 404
    
    # Create Plotly charts
    charts = {}
    
    # 1. Cases Over Time
    fig_cases = go.Figure()
    fig_cases.add_trace(go.Scatter(
        x=data['date'],
        y=data['cases'],
        mode='lines',
        name='Total Cases',
        line=dict(color='#3366CC', width=3)
    ))
    fig_cases.add_trace(go.Scatter(
        x=data['date'],
        y=data['deaths'],
        mode='lines',
        name='Total Deaths',
        line=dict(color='#DC3912', width=3)
    ))
    if 'recovered' in data.columns and not data['recovered'].isna().all():
        fig_cases.add_trace(go.Scatter(
            x=data['date'],
            y=data['recovered'],
            mode='lines',
            name='Recovered',
            line=dict(color='#109618', width=3)
        ))
    fig_cases.update_layout(
        title='COVID-19 Cases Over Time',
        xaxis_title='Date',
        yaxis_title='Number of Cases',
        hovermode='x unified',
        template='plotly_white'
    )
    charts['cases_over_time'] = json.dumps(fig_cases, cls=plotly.utils.PlotlyJSONEncoder)
    
    # 2. Daily New Cases
    if 'new_cases' in data.columns:
        fig_daily = go.Figure()
        fig_daily.add_trace(go.Bar(
            x=data['date'],
            y=data['new_cases'],
            name='New Cases',
            marker_color='#FF6B6B'
        ))
        fig_daily.add_trace(go.Bar(
            x=data['date'],
            y=data['new_deaths'],
            name='New Deaths',
            marker_color='#4A4A4A'
        ))
        fig_daily.update_layout(
            title='Daily New Cases and Deaths',
            xaxis_title='Date',
            yaxis_title='Number of Cases',
            barmode='group',
            template='plotly_white'
        )
        charts['daily_new_cases'] = json.dumps(fig_daily, cls=plotly.utils.PlotlyJSONEncoder)
    
    return jsonify(charts)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
